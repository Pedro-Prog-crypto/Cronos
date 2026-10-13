import json
import asyncio
from dataclasses import replace
from uuid import uuid4
from zipfile import ZipFile

import pytest
import httpx
from fastapi.testclient import TestClient

from cronos.app import create_app
from cronos.config import Settings
from cronos.memory import Memory, topic_filename
from cronos.providers import Gemini, Ollama, ProviderError, parse_reply
from cronos.windows_agent import safe_extract


@pytest.fixture
def settings(tmp_path):
    personality = tmp_path / "personality.md"
    personality.write_text("Critique premissas e reconheça incerteza.", encoding="utf-8")
    return Settings(tmp_path / "vault", personality, "test-token", "gemini", "", "gemini-2.5-flash",
                    "", "", "s1", "http://127.0.0.1:11434", "gemma3:4b",gemini_transport='rest')


AUTH = {"Authorization": "Bearer test-token"}


def test_interface_and_assets(settings):
    with TestClient(create_app(settings)) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert 'lang="pt-BR"' in page.text
        assert 'id="root"' in page.text
        assert 'id="chat-form"' in client.get('/tests').text
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/static/styles.css").status_code == 200
        # Interface pública não concede acesso ao histórico.
        assert client.get(f"/conversations/{uuid4()}").status_code == 401


class FakeProvider:
    def __init__(self):
        self.calls = []

    async def reply(self, system, messages):
        self.calls.append((system, messages))
        return {"reply": "Vamos examinar essa ideia.", "topics": [
            {"title": "Sócrates", "summary": "O usuário perguntou sobre Sócrates."},
            {"title": "Equações", "summary": "O usuário perguntou sobre equações."},
        ]}


def test_chat_persists_reuses_context_and_separates_notes(settings):
    provider = FakeProvider()
    with TestClient(create_app(settings, provider)) as client:
        response = client.post("/chat", headers=AUTH, json={"message": "Sócrates e equações?"})
        assert response.status_code == 200
        result = response.json()
        assert len(result["notes"]) == 2
        first = settings.vault / result["notes"][0]
        assert "Sócrates" in first.read_text()
        assert "O usuário perguntou sobre equações." not in first.read_text()
        assert "Relacionadas:" in first.read_text()
        second = client.post("/chat", headers=AUTH, json={"message": "E Sócrates?", "session_id": result["session_id"]})
        assert second.status_code == 200
        assert len(provider.calls[1][1]) == 3
        assert "O usuário perguntou sobre Sócrates" in provider.calls[1][0]
        history = client.get(f"/conversations/{result['session_id']}", headers=AUTH).json()
        assert len(history["messages"]) == 4
    # Reiniciar a API preserva histórico no disco.
    with TestClient(create_app(settings, provider)) as client:
        assert len(client.get(f"/conversations/{result['session_id']}", headers=AUTH).json()["messages"]) == 4
    assert len(list((settings.vault / "Temas").glob("*.md"))) == 2


def test_authentication_and_missing_configuration(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/chat", json={"message": "Olá"}).status_code == 401
        assert client.post("/chat", headers=AUTH, json={"message": "Olá"}).status_code == 503
        assert client.post("/voice/speech", headers=AUTH, json={"text": "Olá"}).status_code == 503
        assert client.post("/chat", headers=AUTH, json={"message": "  "}).status_code == 422
        assert client.get("/conversations/not-a-uuid", headers=AUTH).status_code == 422
    with TestClient(create_app(replace(settings, token=""))) as client:
        assert client.get("/status", headers=AUTH).status_code == 503
    assert not list((settings.vault / "Conversas").glob("*.md"))


def test_provider_failure_does_not_write_memory(settings):
    class Failing:
        async def reply(self, *args):
            raise ProviderError("Falha simulada")
    with TestClient(create_app(settings, Failing())) as client:
        assert client.post("/chat", headers=AUTH, json={"message": "Olá"}).status_code == 503
    assert not list((settings.vault / "Temas").glob("*.md"))


def test_model_output_validation():
    assert parse_reply('{"reply":"Olá","topics":[]}')["reply"] == "Olá"
    for bad in ("texto", '[]', '{"reply":"ok","topics":["Sócrates"]}', '{"reply":"","topics":[]}'):
        with pytest.raises(ProviderError):
            parse_reply(bad)


def test_memory_paths_and_case_matching(tmp_path):
    assert topic_filename("Sócrates") == topic_filename("SÓCRATES")
    assert "/" not in topic_filename("../../segredo")
    memory = Memory(tmp_path / "vault")
    external = tmp_path / "outside.md"
    external.write_text("privado")
    (memory.vault / "Temas" / "link.md").symlink_to(external)
    with pytest.raises(ValueError):
        memory.recall("privado")


def test_zip_traversal_and_existing_destination(tmp_path):
    archive = tmp_path / "bad.zip"
    with ZipFile(archive, "w") as file:
        file.writestr("../outside.txt", "unsafe")
    with pytest.raises(ValueError):
        safe_extract(archive, tmp_path / "out")
    assert not (tmp_path / "outside.txt").exists()
    with ZipFile(archive, "w") as file:
        file.writestr("folder/note.md", "ok")
    safe_extract(archive, tmp_path / "out")
    assert (tmp_path / "out/folder/note.md").read_text() == "ok"
    with pytest.raises(ValueError):
        safe_extract(archive, tmp_path / "out")


def test_voice_contract(settings):
    class FakeFish:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        @property
        def tts(self): return self
        @property
        def asr(self): return self
        async def convert(self, **kwargs):
            assert kwargs["reference_id"] == "voice-id"
            assert kwargs["format"] == "mp3"
            return b"fake-mp3"
        async def transcribe(self, **kwargs):
            assert kwargs["audio"] == b"test-audio"
            return type("Transcript", (), {"text": "Olá Cronos"})()
    configured = replace(settings, fish_key="test-key", fish_reference="voice-id")
    with TestClient(create_app(configured, fish_factory=FakeFish)) as client:
        speech = client.post("/voice/speech", headers=AUTH, json={"text": "Olá"})
        assert speech.status_code == 200 and speech.content == b"fake-mp3"
        assert speech.headers["content-type"] == "audio/mpeg"
        assert client.post("/voice/transcribe", headers=AUTH, content=b"test-audio").json() == {"text": "Olá Cronos"}
        assert client.post("/voice/transcribe", headers=AUTH, content=b"").status_code == 422
        assert client.post("/voice/transcribe", headers=AUTH, content=b"x" * (10 * 1024 * 1024 + 1)).status_code == 413


def test_gemini_http_contract_and_quota_error(settings, monkeypatch):
    original_client = httpx.AsyncClient
    captured = []
    def handler(request):
        captured.append(request)
        if len(captured) == 2:
            return httpx.Response(429, json={"error": {"message": "sensitive provider error"}})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [
            {"text": '{"reply":"Olá","topics":[]}'}
        ]}}]})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(handler)))
    provider = Gemini(replace(settings, gemini_key="dummy-key"))
    assert asyncio.run(provider.reply("Personalidade", [{"role": "user", "content": "Olá"}]))["reply"] == "Olá"
    assert captured[0].url.host == "generativelanguage.googleapis.com"
    assert captured[0].headers["x-goog-api-key"] == "dummy-key"
    assert json.loads(captured[0].content)["generationConfig"]["responseMimeType"] == "application/json"
    with pytest.raises(ProviderError, match="cota") as error:
        asyncio.run(provider.reply("Personalidade", [{"role": "user", "content": "Olá"}]))
    assert "sensitive" not in str(error.value)


def test_ollama_http_contract(settings, monkeypatch):
    original_client = httpx.AsyncClient
    def handler(request):
        body = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert body["stream"] is False
        assert body["messages"][0]["role"] == "system"
        return httpx.Response(200, json={"message": {"content": '{"reply":"Local","topics":[]}'}})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(handler)))
    assert asyncio.run(Ollama(settings).reply("Personalidade", [{"role": "user", "content": "Olá"}]))["reply"] == "Local"


@pytest.mark.parametrize("status,reason,expected", [
    (400, "API_KEY_INVALID", "chave rejeitada"),
    (403, "SERVICE_DISABLED", "API está desativada"),
    (401, "", "chave rejeitada"),
    (403, "", "acesso negado"),
    (404, "", "modelo não encontrado"),
    (429, "", "cota esgotada"),
    (400, "", "solicitação rejeitada"),
    (503, "", "falha no serviço Google"),
])
def test_gemini_error_diagnosis_without_secret_leak(settings, monkeypatch, status, reason, expected):
    original_client = httpx.AsyncClient
    def handler(request):
        return httpx.Response(status, json={"error": {"message": "PRIVATE_KEY_AND_PROMPT", "details": [{"reason": reason}]}})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ProviderError, match=expected) as error:
        asyncio.run(Gemini(replace(settings, gemini_key="dummy")).reply("Test", [{"role": "user", "content": "Olá"}]))
    assert "PRIVATE_KEY_AND_PROMPT" not in str(error.value)


@pytest.mark.parametrize("failure,expected", [(httpx.ConnectError, "conectar"), (httpx.ReadTimeout, "tempo de resposta")])
def test_gemini_network_diagnosis(settings, monkeypatch, failure, expected):
    original_client = httpx.AsyncClient
    def handler(request):
        raise failure("sensitive error", request=request)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ProviderError, match=expected):
        asyncio.run(Gemini(replace(settings, gemini_key="dummy")).reply("Test", [{"role": "user", "content": "Olá"}]))
