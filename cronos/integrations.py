"""Adaptadores configuráveis: cada credencial continua fora do manifesto."""
import json
import os
import re
from dataclasses import replace
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from cronos.providers import Gemini, Ollama, OUTPUT_RULES, ProviderError, parse_completed_reply


class ProviderSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    kind: str = Field(pattern=r"^(openai|anthropic|gemini|ollama)$")
    model: str = Field(min_length=1, max_length=200)
    base_url: str = ""
    key_env: str = Field(default="", pattern=r"^([A-Za-z_][A-Za-z0-9_]*)?$")
    max_output_tokens: int | None = Field(default=None, ge=128)
    timeout_seconds: float = Field(default=180, ge=1)

    @field_validator('key_env')
    @classmethod
    def protect_internal_variables(cls, value):
        if value.upper().startswith('CRONOS_') or value.upper() in {'PATH', 'HOME', 'USERPROFILE', 'SYSTEMROOT'}:
            raise ValueError('Não use variáveis internas como credencial de um provedor.')
        return value


def specs(settings):
    if not settings.providers_file.exists():
        return []
    try:
        data = json.loads(settings.providers_file.read_text(encoding="utf-8-sig"))
        entries = [ProviderSpec.model_validate(item) for item in data["providers"]]
        if len({p.id for p in entries}) != len(entries) or any(p.id in {"gemini", "ollama"} for p in entries):
            raise ValueError()
        return entries
    except (OSError, ValueError, TypeError, KeyError, ValidationError) as exc:
        raise ProviderError("Manifesto de provedores inválido. Confira config/providers.json; IDs devem ser únicos.") from exc


def checked_url(url):
    parsed = urlsplit(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname:
        raise ProviderError("Endereço de provedor inválido: não inclua credenciais, query ou fragmento na URL.")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}):
        raise ProviderError("Use HTTPS para provedores externos; HTTP é permitido apenas em loopback.")
    return url.rstrip("/")


class CompatibleProvider:
    def __init__(self, spec):
        self.spec = spec

    async def reply(self, system, messages):
        spec = self.spec
        key = os.getenv(spec.key_env, "").strip() if spec.key_env else ""
        if spec.key_env and not key:
            raise ProviderError(f"Configure {spec.key_env} para usar {spec.id}.")
        base = checked_url(spec.base_url)
        if spec.kind == "anthropic":
            path = "/messages"
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
            payload = {"model": spec.model, "max_tokens": spec.max_output_tokens or 8192,
                       "system": system + "\n" + OUTPUT_RULES, "messages": messages}
        else:
            path = "/chat/completions"
            headers = {"Authorization": "Bearer " + key} if key else {}
            payload = {"model": spec.model,
                       "messages": [{"role": "system", "content": system + "\n" + OUTPUT_RULES}, *messages],
                       "response_format": {"type": "json_object"}}
            if spec.max_output_tokens:
                payload["max_tokens"] = spec.max_output_tokens
        try:
            async with httpx.AsyncClient(timeout=spec.timeout_seconds) as client:
                response = await client.post(base + path, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                if spec.kind == "anthropic":
                    raw = "".join(part["text"] for part in data["content"] if part.get("type") == "text")
                    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
                else:
                    raw = data["choices"][0]["message"]["content"]
                return parse_completed_reply(raw)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            reason = {401: "chave rejeitada", 403: "acesso negado", 404: "modelo ou endpoint indisponível",
                      429: "cota esgotada ou limite de chamadas", 400: "requisição ou formato JSON não aceito"}.get(status, "serviço indisponível")
            raise ProviderError(f"{spec.id}: {reason} (HTTP {status}).", status) from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"{spec.id}: falha de conexão ou tempo esgotado.") from exc
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise ProviderError(f"{spec.id}: resposta incompatível com o formato esperado.") from exc


def configured_provider(settings, provider_id=None):
    provider_id = provider_id or settings.provider
    spec = next((entry for entry in specs(settings) if entry.id == provider_id), None)
    if not spec:
        raise ProviderError("Provedor não registrado. Configure seu adaptador em config/providers.json.")
    if settings.privacy_mode != 'online' and spec.kind != 'ollama':
        raise ProviderError("Modo local: provedores externos estão desabilitados.")
    if spec.kind == "gemini":
        return Gemini(replace(settings, gemini_transport='rest',gemini_model=spec.model, gemini_key=os.getenv(spec.key_env, ""),
                              output_tokens=spec.max_output_tokens, provider_timeout=spec.timeout_seconds))
    if spec.kind == "ollama":
        return Ollama(replace(settings, ollama_model=spec.model, ollama_url=checked_url(spec.base_url),
                              output_tokens=spec.max_output_tokens, provider_timeout=spec.timeout_seconds))
    return CompatibleProvider(spec)


def provider_catalog(settings):
    entries = [{"id": "gemini", "kind": "gemini", "model": settings.gemini_live_model if settings.gemini_transport=='live' else settings.gemini_model, "configured": bool(settings.gemini_key)},
               {"id": "ollama", "kind": "ollama", "model": settings.ollama_model, "configured": True}]
    entries.extend({"id": spec.id, "kind": spec.kind, "model": spec.model,
                    "configured": not spec.key_env or bool(os.getenv(spec.key_env))} for spec in specs(settings))
    for entry in entries:
        entry['allowed'] = settings.privacy_mode == 'online' or entry['kind'] == 'ollama'
        entry['configured'] = entry['configured'] and entry['allowed']
    return entries


async def available_models(settings, provider_id):
    """Descoberta explícita, sem geração ou escolha automática de modelo pago."""
    if provider_id == "gemini":
        kind, base, key = "gemini", "https://generativelanguage.googleapis.com/v1beta", settings.gemini_key.strip()
    elif provider_id == "ollama":
        kind, base, key = "ollama", checked_url(settings.ollama_url), ""
    else:
        spec = next((item for item in specs(settings) if item.id == provider_id), None)
        if not spec:
            raise ProviderError("Provedor não registrado.")
        kind, base, key = spec.kind, checked_url(spec.base_url) if spec.base_url else "", os.getenv(spec.key_env, "").strip()
        if spec.key_env and not key:
            raise ProviderError(f"Configure {spec.key_env} para listar os modelos de {provider_id}.")
        if kind == "gemini":
            base = "https://generativelanguage.googleapis.com/v1beta"
    if kind in {"gemini", "anthropic"} and not key:
        raise ProviderError("Configure a chave do provedor antes de listar modelos.")
    if settings.privacy_mode != 'online':
        if kind != 'ollama':
            raise ProviderError("Modo local: consulta a provedores externos está desabilitada.")
        from cronos.security import local_endpoint, SecurityError
        try:
            local_endpoint(base)
        except SecurityError as exc:
            raise ProviderError(str(exc)) from exc
    headers = ({"x-goog-api-key": key} if kind == "gemini" else
               {"x-api-key": key, "anthropic-version": "2023-06-01"} if kind == "anthropic" else
               {"Authorization": "Bearer " + key} if key else {})
    models, token, seen = [], None, set()
    try:
        async with httpx.AsyncClient(timeout=settings.provider_timeout) as client:
            for _ in range(10):
                params = {"pageToken": token} if token and kind == "gemini" else {"after_id": token} if token and kind == "anthropic" else {}
                response = await client.get(base + ("/api/tags" if kind == "ollama" else "/models"), headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                if kind == "gemini":
                    models.extend(item['name'].removeprefix('models/') for item in data.get('models', [])
                                  if 'generateContent' in item.get('supportedGenerationMethods', []))
                    token = data.get('nextPageToken')
                elif kind == "ollama":
                    models.extend(item['name'] for item in data.get('models', []))
                else:
                    models.extend(item['id'] for item in data.get('data', []))
                    if kind == "anthropic":
                        token = data.get('last_id') if data.get('has_more') else None
                if not token:
                    return sorted(set(models))
                if token in seen:
                    break
                seen.add(token)
        raise ProviderError("A listagem de modelos veio incompleta; confira o painel do provedor.")
    except httpx.HTTPStatusError as exc:
        raise ProviderError(f"Não foi possível listar modelos (HTTP {exc.response.status_code}). Confira chave, acesso e endpoint.") from exc
    except (httpx.RequestError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ProviderError("Falha de conexão ou formato na listagem de modelos.") from exc
