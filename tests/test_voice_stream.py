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
    settings = replace(Settings.from_env(), vault=tmp_path / "vault", token="test-token", fish_key="dummy", fish_model="s1", fish_reference="voice-id")
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
    settings = replace(Settings.from_env(), vault=tmp_path / "vault", token="test-token", fish_key="dummy", fish_model="s1")
    with TestClient(create_app(settings, fish_factory=Fish)) as client:
        for endpoint, expected in (("/voice/stream", "chave rejeitada"), ("/voice/speech", "HTTP 402")):
            response = client.post(endpoint, headers={"Authorization": "Bearer test-token"}, json={"text": "Olá"})
            assert response.status_code == 502
            assert expected in response.json()["detail"]
            assert "SECRET_PROVIDER_ERROR" not in response.text


def test_microphone_billing_error_identifies_asr_without_claiming_zero_balance(tmp_path):
    class Fish:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        @property
        def asr(self):return self
        async def transcribe(self,**kwargs):raise APIError(402,'PRIVATE_ERROR','PRIVATE_BODY')
    settings=replace(Settings.from_env(),vault=tmp_path/'vault',token='test-token',fish_key='dummy',fish_model='s2-pro')
    with TestClient(create_app(settings,fish_factory=Fish)) as client:
        response=client.post('/voice/transcribe',headers={'Authorization':'Bearer test-token','Content-Type':'audio/webm'},content=b'audio')
        assert response.status_code==502
        assert 'transcrição do microfone' in response.text and 'HTTP 402' in response.text
        assert 'não confirma saldo zerado' in response.text
        assert 'PRIVATE' not in response.text


def test_billing_error_does_not_guess_another_model(tmp_path):
    calls=[]
    class Fish:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        @property
        def tts(self):return self
        async def convert(self,**kwargs):
            calls.append(kwargs)
            raise APIError(402,'private')
    settings=replace(Settings.from_env(),vault=tmp_path/'vault',token='test-token',fish_key='dummy',fish_model='s2-pro',fish_reference='same-voice')
    with TestClient(create_app(settings,fish_factory=Fish)) as client:
        response=client.post('/voice/speech',headers={'Authorization':'Bearer test-token'},json={'text':'Olá'})
        assert response.status_code==502
    assert len(calls)==1 and calls[0]['model']=='s2-pro'
    assert calls[0]['reference_id']=='same-voice'


def test_real_sdk_can_send_legacy_model_identifier():
    import asyncio,httpx,ormsgpack
    from fishaudio import AsyncFishAudio
    captured=[]
    def request(request):
        captured.append(request)
        return httpx.Response(200,content=b'audio',headers={'Content-Type':'audio/mpeg'})
    async def run():
        async with httpx.AsyncClient(base_url="https://api.fish.audio",transport=httpx.MockTransport(request)) as transport:
            async with AsyncFishAudio(api_key='dummy-test',httpx_client=transport) as fish:
                assert await fish.tts.convert(text='Olá',model='s2.1-pro-free',reference_id='same-voice',format='mp3')==b'audio'
    asyncio.run(run())
    assert captured[0].url.path=='/v1/tts'
    assert captured[0].headers['model']=='s2.1-pro-free'
    assert ormsgpack.unpackb(captured[0].content)['reference_id']=='same-voice'
