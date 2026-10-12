import json
from typing import Protocol

import httpx

from cronos.config import Settings


class ProviderError(Exception):
    pass


class Provider(Protocol):
    async def reply(self, system: str, messages: list[dict]) -> dict: ...


OUTPUT_RULES = '''Retorne somente JSON no formato:
{"reply":"resposta ao usuário","topics":[{"title":"tema específico","summary":"registro apenas deste tema"}]}.
Identifique até 5 assuntos realmente discutidos na mensagem atual. Use nomes
estáveis: "Sócrates", "Equações quadráticas". Se não há tema significativo,
retorne topics vazio. Nunca crie notas sobre assuntos que não foram discutidos.
Em summary, separe o que o usuário afirmou/perguntou do que a IA respondeu.
Não misture assuntos diferentes numa mesma nota e não invente detalhes pessoais.'''


def parse_reply(raw: str) -> dict:
    try:
        data = json.loads(raw)
        if not isinstance(data.get("reply"), str) or not data["reply"].strip():
            raise ValueError()
        topics = data.get("topics", [])
        if not isinstance(topics, list) or len(topics) > 5 or any(
            not isinstance(t, dict) or not isinstance(t.get("title"), str)
            or not t["title"].strip() or len(t["title"]) > 120
            or not isinstance(t.get("summary"), str) or not t["summary"].strip()
            or len(t["summary"]) > 8000 for t in topics
        ):
            raise ValueError()
        unique = {t["title"].strip().casefold(): {"title": t["title"].strip(), "summary": t["summary"]} for t in topics}
        return {"reply": data["reply"], "topics": list(unique.values())}
    except (ValueError, TypeError, AttributeError) as exc:
        raise ProviderError("O modelo retornou uma resposta fora do formato esperado.") from exc


class Gemini:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def reply(self, system, messages):
        key = self.settings.gemini_key.strip()
        if not key:
            raise ProviderError("Configure GEMINI_API_KEY para usar o Gemini.")
        model = self.settings.gemini_model
        if not model or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._" for c in model):
            raise ProviderError("GEMINI_MODEL inválido.")
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={"x-goog-api-key": key},
                    json={
                        "systemInstruction": {"parts": [{"text": system + "\n" + OUTPUT_RULES}]},
                        "contents": [{"role": "model" if m["role"] == "assistant" else "user",
                                      "parts": [{"text": m["content"]}]} for m in messages],
                        "generationConfig": {"responseMimeType": "application/json"},
                    },
                )
                response.raise_for_status()
                data = response.json()
                if data.get("promptFeedback", {}).get("blockReason"):
                    raise ProviderError("Gemini bloqueou esta solicitação. Tente reformular a mensagem.")
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ProviderError("Gemini não retornou uma resposta. Tente uma mensagem curta de teste.")
                candidate = candidates[0]
                if candidate.get("finishReason") == "MAX_TOKENS":
                    raise ProviderError("Gemini atingiu o limite de saída. Reduza a mensagem ou o contexto da conversa.")
                raw = "".join(p.get("text", "") for p in candidate["content"]["parts"])
                return parse_reply(raw)
        except httpx.HTTPStatusError as exc:
            # Classificar somente códigos/reasons estruturados; não ecoar o corpo,
            # que pode incluir a chave ou conteúdo pessoal.
            status = exc.response.status_code
            reasons = set()
            try:
                details = exc.response.json().get("error", {}).get("details", [])
                reasons = {d.get("reason") for d in details if isinstance(d, dict) and isinstance(d.get("reason"), str)}
            except (ValueError, AttributeError, TypeError):
                pass
            if "API_KEY_INVALID" in reasons or status == 401:
                message = "Gemini: chave rejeitada. Confira GEMINI_API_KEY no .env; use uma chave da API do Google AI Studio e reinicie o Cronos."
            elif "SERVICE_DISABLED" in reasons:
                message = "Gemini: a API está desativada no projeto Google associado à chave. Verifique a habilitação da Generative Language API nesse projeto."
            elif status == 403:
                message = "Gemini: acesso negado (HTTP 403). Verifique as restrições da chave e as permissões do projeto Google."
            elif status == 404:
                message = "Gemini: modelo não encontrado ou indisponível para esta chave (HTTP 404). Confira GEMINI_MODEL no .env e os modelos disponíveis no Google AI Studio."
            elif status == 429:
                message = "Gemini: cota esgotada ou limite de requisições atingido (HTTP 429). Confira os limites do projeto no Google AI Studio; aguardar só resolve limites temporários."
            elif status == 400:
                message = "Gemini: solicitação rejeitada (HTTP 400). Confira a chave, a disponibilidade do modelo e o suporte a respostas JSON; a causa precisa ser verificada no projeto Google."
            elif status >= 500:
                message = f"Gemini: falha no serviço Google (HTTP {status}). Tente novamente mais tarde."
            else:
                message = f"Gemini: chamada rejeitada (HTTP {status}). Verifique o acesso à API no projeto Google."
            raise ProviderError(message) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError("Gemini: tempo de resposta esgotado. Confira a conexão e tente novamente.") from exc
        except httpx.RequestError as exc:
            raise ProviderError("Gemini: não foi possível conectar à API Google. Confira internet, DNS, proxy e certificados do Windows.") from exc
        except (KeyError, IndexError, ValueError, TypeError, AttributeError) as exc:
            raise ProviderError("Gemini respondeu, mas o conteúdo veio incompleto ou em formato inesperado. Tente uma mensagem curta ou outra conversa.") from exc


class Ollama:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def reply(self, system, messages):
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                response = await client.post(self.settings.ollama_url.rstrip("/") + "/api/chat", json={
                    "model": self.settings.ollama_model, "stream": False, "format": "json",
                    "messages": [{"role": "system", "content": system + "\n" + OUTPUT_RULES}, *messages],
                })
                response.raise_for_status()
                return parse_reply(response.json()["message"]["content"])
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ProviderError("Ollama indisponível; confira o serviço e o modelo instalado.") from exc


PROVIDERS = {"gemini": Gemini, "ollama": Ollama}


def make_provider(settings: Settings) -> Provider:
    try:
        return PROVIDERS[settings.provider](settings)
    except KeyError as exc:
        raise ProviderError("Provedor não registrado.") from exc
