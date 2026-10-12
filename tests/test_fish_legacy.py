import asyncio,json
import httpx
import pytest
from fishaudio.exceptions import APIError
from cronos.fish_legacy import synthesize_json


def test_legacy_request_matches_old_json_endpoint_and_preserves_voice():
    requests=[]
    def respond(request):
        requests.append(request)
        return httpx.Response(200,content=b'audio')
    assert asyncio.run(synthesize_json('dummy-test-key',text='Olá',reference_id='same-voice',speed=1.2,
        transport=httpx.MockTransport(respond)))==b'audio'
    request=requests[0]
    assert str(request.url)=='https://api.fish.audio/v1/tts'
    assert request.headers['model']=='s2.1-pro-free'
    assert request.headers['content-type']=='application/json'
    assert json.loads(request.content)=={'text':'Olá','format':'mp3','latency':'balanced','normalize':True,
        'reference_id':'same-voice','prosody':{'speed':1.2,'volume':0,'normalize_loudness':True}}


def test_legacy_failure_keeps_status_and_hides_provider_body():
    def respond(request):return httpx.Response(402,content=b'PRIVATE_PROVIDER_BODY')
    with pytest.raises(APIError) as failure:
        asyncio.run(synthesize_json('dummy-test-key',text='Olá',transport=httpx.MockTransport(respond)))
    assert failure.value.status==402
    assert 'PRIVATE' not in str(failure.value)
    assert 'dummy-test-key' not in str(failure.value)


def test_legacy_refuses_redirects_and_empty_audio():
    def redirect(request):return httpx.Response(302,headers={'Location':'https://untrusted.example'})
    with pytest.raises(APIError):
        asyncio.run(synthesize_json('dummy',text='Olá',transport=httpx.MockTransport(redirect)))
    with pytest.raises(ValueError,match='vazio'):
        asyncio.run(synthesize_json('dummy',text='Olá',transport=httpx.MockTransport(lambda request:httpx.Response(200,content=b''))))


def test_isolated_windows_voice_test_does_not_open_ui_or_expose_secrets(monkeypatch):
    import sys,ctypes
    from types import SimpleNamespace
    from cronos import voice_diagnostic
    state={};messages=[]
    monkeypatch.setattr(voice_diagnostic,'load_dotenv',lambda *args:None)
    monkeypatch.setattr(voice_diagnostic,'sys',SimpleNamespace(platform='win32'))
    monkeypatch.setattr(voice_diagnostic.Settings,'from_env',lambda:SimpleNamespace(privacy_mode='online',fish_key='dummy-secret',fish_reference='same-voice'))
    async def synthesize(key,**kwargs):state.update(kwargs);return b'wav'
    monkeypatch.setattr(voice_diagnostic,'synthesize_json',synthesize)
    monkeypatch.setitem(sys.modules,'winsound',SimpleNamespace(SND_MEMORY=4,PlaySound=lambda audio,flags:state.update(played=(audio,flags))))
    monkeypatch.setattr(ctypes,'windll',SimpleNamespace(user32=SimpleNamespace(MessageBoxW=lambda handle,text,*args:messages.append(text))),raising=False)
    voice_diagnostic.main()
    assert state['format']=='wav' and state['reference_id']=='same-voice'
    assert state['played']==(b'wav',4)
    assert messages and 'dummy-secret' not in messages[0]


def test_bad_request_exposes_sanitized_reason_not_key_or_voice():
    def response(request):return httpx.Response(400,json={'detail':[{'msg':'Unsupported model: s2.1-pro-free; key=dummy-secret voice=same-voice','input':'PRIVATE_VALUE'}]})
    with pytest.raises(APIError) as failure:
        asyncio.run(synthesize_json('dummy-secret',text='Olá',reference_id='same-voice',transport=httpx.MockTransport(response)))
    assert failure.value.status==400
    assert 'Unsupported model: s2.1-pro-free' in failure.value.safe_detail
    assert 'dummy-secret' not in failure.value.safe_detail and 'same-voice' not in failure.value.safe_detail
    assert 'PRIVATE_VALUE' not in failure.value.safe_detail
