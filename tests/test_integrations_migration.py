import asyncio
import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from dotenv import dotenv_values

from cronos.config import Settings
from cronos.integrations import CompatibleProvider, ProviderSpec, available_models, checked_url, provider_catalog
from cronos.memory import Memory
from cronos.migrate import apply_env, import_facts, prepare
from cronos.providers import ProviderError, make_provider


@pytest.mark.parametrize("kind", ["openai", "anthropic"])
def test_compatible_provider_contracts(kind, monkeypatch):
    monkeypatch.setenv("TEST_MODEL_KEY", "test-key")
    original = httpx.AsyncClient
    def handler(request):
        payload = json.loads(request.content)
        assert payload["model"] == "configured-model"
        if kind == "openai":
            assert request.url.path == "/v1/chat/completions"
            assert request.headers["authorization"] == "Bearer test-key"
            assert payload["messages"][0]["role"] == "system"
            return httpx.Response(200, json={"choices": [{"message": {"content": '{"reply":"Resposta independente","topics":[]}'}}]})
        assert request.url.path == "/v1/messages"
        assert request.headers["x-api-key"] == "test-key"
        assert payload["system"].startswith("Personalidade")
        return httpx.Response(200, json={"content": [{"type": "text", "text": '```json\n{"reply":"Resposta independente","topics":[]}\n```'}]})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler)))
    spec = ProviderSpec(id="test", kind=kind, base_url="https://models.example/v1", model="configured-model", key_env="TEST_MODEL_KEY")
    result = asyncio.run(CompatibleProvider(spec).reply("Personalidade", [{"role": "user", "content": "Pergunta"}]))
    assert result["reply"] == "Resposta independente"


def test_manifest_supports_many_providers_and_missing_keys(tmp_path, monkeypatch):
    monkeypatch.delenv("MISSING_TEST_KEY", raising=False)
    file = tmp_path / "providers.json"
    file.write_text(json.dumps({"providers": [{"id": f"provider-{i}", "kind": "openai", "base_url": "https://api.example/v1",
                                              "model": "user-model", "key_env": "MISSING_TEST_KEY"} for i in range(50)]}))
    settings = replace(Settings.from_env(), providers_file=file, provider="provider-49")
    assert len(provider_catalog(settings)) == 52
    with pytest.raises(ProviderError, match="MISSING_TEST_KEY"):
        asyncio.run(make_provider(settings).reply("System", [{"role": "user", "content": "Olá"}]))
    file.write_text('{"providers":[{"id":"gemini","kind":"openai","model":"x"}]}')
    with pytest.raises(ProviderError, match="Manifesto"):
        provider_catalog(settings)


@pytest.mark.parametrize("url", ["http://api.example/v1", "https://user:password@api.example", "https://api.example/v1?token=secret"])
def test_external_provider_urls_reject_plaintext_and_embedded_credentials(url):
    with pytest.raises(ProviderError):
        checked_url(url)


def test_migration_preserves_existing_secrets_and_all_fact_content(tmp_path, monkeypatch):
    source = tmp_path / "old"
    (source / "config").mkdir(parents=True)
    (source / "memory").mkdir()
    (source / "config/api_keys.json").write_text(json.dumps({"gemini_api_key": "old-dummy-key"}))
    (source / "config/fish_audio.json").write_text(json.dumps({"api_key": "fish-dummy-key", "reference_id": "voice", "model": "s2-pro"}))
    (source / "config/storage.json").write_text(json.dumps({"obsidian_vault": "Obsidian"}))
    full_value = "relato longo " * 100
    facts = source / "memory/long_term.json"
    original = json.dumps({"preferences": {"project": {"value": full_value}}})
    facts.write_text(original)
    target = tmp_path / ".env"
    target.write_text("GEMINI_API_KEY=already-configured\nFISH_API_KEY=\n")
    for name in ("GEMINI_API_KEY", "FISH_API_KEY", "FISH_MODEL", "FISH_REFERENCE_ID", "CRONOS_VAULT"):
        monkeypatch.delenv(name, raising=False)
    values, fact_file = prepare(source)
    assert values["CRONOS_VAULT"] == str(source / "Obsidian")
    added = apply_env(target, values)
    assert "GEMINI_API_KEY" not in added
    assert dotenv_values(target)["GEMINI_API_KEY"] == "already-configured"
    assert dotenv_values(target)["FISH_API_KEY"] == "fish-dummy-key"
    memory = Memory(tmp_path / "new-vault")
    assert import_facts(memory, fact_file) == 1
    assert import_facts(memory, fact_file) == 0
    assert full_value in next((memory.vault / "Temas").glob("*.md")).read_text()
    assert facts.read_text() == original


def test_available_gemini_models_are_paginated_without_generation(monkeypatch):
    original = httpx.AsyncClient
    requests = []
    def handler(request):
        requests.append(request)
        assert request.method == "GET" and request.url.path.endswith("/models")
        assert request.headers["x-goog-api-key"] == "test-key"
        if len(requests) == 1:
            return httpx.Response(200, json={"models": [{"name": "models/chat-a", "supportedGenerationMethods": ["generateContent"]},
                                                       {"name": "models/embedding", "supportedGenerationMethods": ["embedContent"]}], "nextPageToken": "page2"})
        assert request.url.params["pageToken"] == "page2"
        return httpx.Response(200, json={"models": [{"name": "models/chat-b", "supportedGenerationMethods": ["generateContent"]}]})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler)))
    assert asyncio.run(available_models(replace(Settings.from_env(), gemini_key="test-key"), "gemini")) == ["chat-a", "chat-b"]
