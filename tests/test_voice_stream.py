from dataclasses import replace

from fastapi.testclient import TestClient
from fishaudio.exceptions import APIError, AuthenticationError

from cronos.app import create_app
from cronos.config import Settings


def test_stream_voice_uses_configured_voice_speed_and_closes_client(tmp_path):
    state = {"closed": False}
    class Fish:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): state["closed"] = True
        @property
        def tts(self): return self
        async def stream(self, **kwargs):
            assert kwargs["reference_id"] == "voice-id"
            assert kwargs["speed"] == 1.2
            async def chunks():
                yield b"first"
                yield b"second"
            return chunks()
    settings = replace(Settings.from_env(), vault=tmp_path / "vault", token="test-token", fish_key="dummy", fish_reference="voice-id")
    with TestClient(create_app(settings, fish_factory=Fish)) as client:
        response = client.post("/voice/stream", headers={"Authorization": "Bearer test-token"}, json={"text": "Olá", "speed": 1.2})
        assert response.status_code == 200 and response.content == b"firstsecond"
        assert state["closed"]


def test_voice_error_is_classified_before_stream_headers_without_secret_leak(tmp_path):
    class Fish:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        @property
        def tts(self): return self
        async def stream(self, **kwargs):
            raise AuthenticationError(401, "SECRET_PROVIDER_ERROR")
        async def convert(self, **kwargs):
            raise APIError(402, "SECRET_PROVIDER_ERROR")
    settings = replace(Settings.from_env(), vault=tmp_path / "vault", token="test-token", fish_key="dummy")
    with TestClient(create_app(settings, fish_factory=Fish)) as client:
        for endpoint, expected in (("/voice/stream", "chave rejeitada"), ("/voice/speech", "créditos necessários")):
            response = client.post(endpoint, headers={"Authorization": "Bearer test-token"}, json={"text": "Olá"})
            assert response.status_code == 502
            assert expected in response.json()["detail"]
            assert "SECRET_PROVIDER_ERROR" not in response.text
