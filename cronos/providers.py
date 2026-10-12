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
        if not self.settings.gemini_key:
            raise ProviderError("Configure GEMINI_API_KEY para usar o Gemini.")
        model = self.settings.gemini_model
        if not model or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._" for c in model):
            raise ProviderError("GEMINI_MODEL inválido.")
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={"x-goog-api-key": self.settings.gemini_key},
                    json={
                        "systemInstruction": {"parts": [{"text": system + "\n" + OUTPUT_RULES}]},
                        "contents": [{"role": "model" if m["role"] == "assistant" else "user",
                                      "parts": [{"text": m["content"]}]} for m in messages],
                        "generationConfig": {"responseMimeType": "application/json"},
                    },
                )
                response.raise_for_status()
                raw = "".join(p.get("text", "") for p in response.json()["candidates"][0]["content"]["parts"])
                return parse_reply(raw)
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            # Não expor corpo de erro, chaves ou conteúdo pessoal em logs/respostas.
            raise ProviderError("Gemini indisponível; confira modelo, chave, acesso e cota.") from exc


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
