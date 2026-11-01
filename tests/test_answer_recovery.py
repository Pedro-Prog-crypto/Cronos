"""Regressions for valid answers discarded by nested latency cutoffs."""
import asyncio
import io
import json
import subprocess
import threading
import wave
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from cronos import evolution
from cronos.providers import ProviderError
from cronos.app import create_app
from test_backend import settings,AUTH


def test_slow_complete_answer_is_not_discarded_without_a_reserve(settings, monkeypatch):
    monkeypatch.setattr(evolution, 'FIRST_REPLY_TIMEOUT_SECONDS', .005)
    monkeypatch.setattr(evolution, 'read', lambda _: {'routing': {'enabled': False, 'fallbacks': []}})
    class Primary:
        async def reply(self, *args):
            await asyncio.sleep(.025)
            return {'reply': 'Esta é a resposta real.', 'topics': [], 'tool_calls': []}
    result = asyncio.run(evolution.ResilientProvider(replace(settings, provider_timeout=.2), Primary()).reply('', []))
    assert result['reply'] == 'Esta é a resposta real.'


def test_failed_reserve_does_not_cancel_a_primary_that_will_answer(settings, monkeypatch):
    monkeypatch.setattr(evolution, 'FIRST_REPLY_TIMEOUT_SECONDS', .005)
    monkeypatch.setattr(evolution, 'read', lambda _: {'routing': {'enabled': True, 'fallbacks': ['reserve']}})
    monkeypatch.setattr(evolution, 'provider_catalog', lambda _: [{'id': 'reserve', 'configured': True}])
    calls=[]
    class Primary:
        async def reply(self, *args):
            await asyncio.sleep(.035)
            return {'reply': 'A principal terminou corretamente.', 'topics': [], 'tool_calls': []}
    class Reserve:
        async def reply(self, *args):
            calls.append('reserve')
            raise ProviderError('HTTP 429', 429)
    monkeypatch.setattr('cronos.conversation_transport.conversation_provider', lambda _: Reserve())
    result=asyncio.run(evolution.ResilientProvider(replace(settings, provider_timeout=.2), Primary()).reply('', []))
    assert calls == ['reserve']
    assert result['reply'] == 'A principal terminou corretamente.'


def test_intro_route_identity_survives_python311_child_task_behavior(settings,monkeypatch):
    from cronos.reply_stream import deliver_intro,intro_sink
    original_wait=asyncio.wait_for
    async def child_wait(awaitable,timeout):
        return await original_wait(asyncio.ensure_future(awaitable),timeout)
    monkeypatch.setattr(asyncio,'wait_for',child_wait)
    spoken=[]
    class Primary:
        async def reply(self,*args):
            await deliver_intro('Esta é a primeira frase.')
            await asyncio.sleep(.01)
            return {'reply':'Esta é a primeira frase. E esta é a conclusão.','topics':[],'tool_calls':[]}
    async def run():
        async def intro(value):spoken.append(value)
        token=intro_sink.set(intro)
        try:return await evolution.ResilientProvider(settings,Primary()).reply('',[])
        finally:intro_sink.reset(token)
    assert asyncio.run(run())['reply'].endswith('conclusão.')
    assert spoken==['Esta é a primeira frase.']


def recording(seconds=1):
    result=io.BytesIO()
    with wave.open(result,'wb') as target:
        target.setnchannels(1);target.setsampwidth(2);target.setframerate(16000)
        target.writeframes(b'\x00\x02\x00\xfe'*(8000*seconds))
    return result.getvalue()


def test_local_asr_recovers_same_recording_when_both_cloud_recognizers_fail(settings,monkeypatch,tmp_path):
    from cronos.recognition import LocalRecognizer
    import cronos.transcription as transcription
    monkeypatch.setattr('cronos.wake.verify_model',lambda:tmp_path)
    audio=recording();calls=[]
    def local(self,value):
        assert value==audio;calls.append('local')
        return 'Cronos, qual é a capital do Brasil?'
    async def failed(*args):raise ProviderError('Reconhecimento externo indisponível',503)
    monkeypatch.setattr(LocalRecognizer,'transcribe',local)
    monkeypatch.setattr(transcription,'gemini_transcribe',failed)
    class Fish:
        def __init__(self):self.asr=self
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def transcribe(self,**kwargs):
            assert kwargs['audio']==audio
            raise RuntimeError('unavailable')
    with TestClient(create_app(replace(settings,fish_key='fixture',gemini_key='fixture'),fish_factory=Fish)) as client:
        result=client.post('/voice/transcribe',headers={**AUTH,'Content-Type':'audio/wav'},content=audio)
        assert result.status_code==200 and 'Brasil' in result.json()['text']
    assert calls==['local']


def test_native_three_minute_capture_is_accepted_by_server_validator():
    from cronos.recognition import read_pcm
    assert len(read_pcm(recording(180)))==180*32000
    with pytest.raises(ValueError):read_pcm(recording(181))


def test_direct_live_audio_requires_an_explicit_opt_in(settings):
    configured=replace(settings,gemini_transport='live',gemini_key='fixture')
    for explicit in (False,True):
        with TestClient(create_app(replace(configured,direct_audio_chat=explicit))) as client:
            assert client.get('/status',headers=AUTH).json()['direct_audio_chat'] is explicit


def test_confirmed_wake_allows_question_without_repeating_name(settings):
    from cronos.reply_stream import deliver_transcript
    class Provider:
        async def reply(self,*args):
            await deliver_transcript('Qual é a capital do Brasil?')
            return {'recognized_text':'Qual é a capital do Brasil?','reply':'A capital é Brasília.','topics':[],'tool_calls':[]}
    with TestClient(create_app(replace(settings,gemini_transport='live'),Provider())) as client:
        client.patch('/panels/preferences',headers=AUTH,json={'called_only':True})
        for confirmed in (False,True):
            response=client.post('/chat/audio/stream',headers={**AUTH,'Content-Type':'audio/wav',**({'X-Cronos-Wake-Confirmed':'1'} if confirmed else {})},content=recording())
            events=[json.loads(line) for line in response.text.splitlines()]
            result=events[-1]['result']
            if confirmed:assert result['reply']=='A capital é Brasília.' and not result.get('ignored')
            else:assert result['ignored'] and result['reply']==''


def test_invalid_old_routing_does_not_erase_primary_answer(settings,monkeypatch):
    monkeypatch.setattr(evolution,'FIRST_REPLY_TIMEOUT_SECONDS',.001)
    def invalid(_):raise ProviderError('Manifesto antigo inválido.')
    monkeypatch.setattr(evolution,'read',invalid)
    class Primary:
        async def reply(self,*args):
            await asyncio.sleep(.01)
            return {'reply':'A resposta principal está íntegra.','topics':[],'tool_calls':[]}
    assert asyncio.run(evolution.ResilientProvider(settings,Primary()).reply('',[]))['reply'].endswith('íntegra.')


def test_shared_screen_image_does_not_disable_configured_reserves(settings,monkeypatch):
    monkeypatch.setattr(evolution,'read',lambda _: {'routing':{'enabled':True,'fallbacks':['reserve']}})
    monkeypatch.setattr(evolution,'provider_catalog',lambda _: [{'id':'reserve','configured':True}])
    image={'mime_type':'image/jpeg','data':'controlled-image'}
    class Primary:
        async def reply(self,*args):raise ProviderError('quota',429)
    class Reserve:
        async def reply(self,system,messages):
            assert messages[-1]['image']==image
            return {'reply':'A imagem compartilhada chegou à reserva.','topics':[],'tool_calls':[]}
    monkeypatch.setattr('cronos.conversation_transport.conversation_provider',lambda _:Reserve())
    result=asyncio.run(evolution.ResilientProvider(settings,Primary()).reply('',[{'role':'user','content':'Analise a tela','image':image}]))
    assert result['fallback_used'] and result['provider_used']=='reserve'


def test_windows_voice_endpoint_reads_actual_reply_and_respects_auth(settings,monkeypatch):
    from cronos import device_voice
    values=[]
    async def render(text,speed=1):values.append((text,speed));return recording()
    monkeypatch.setattr(device_voice,'synthesize',render)
    with TestClient(create_app(settings)) as client:
        assert client.post('/voice/device',json={'text':'Resposta'}).status_code==401
        result=client.post('/voice/device',headers=AUTH,json={'text':'Brasília é a capital do Brasil.','speed':1.1})
        assert result.status_code==200 and result.content==recording()
        assert result.headers['content-type']=='audio/wav'
    assert values==[('Brasília é a capital do Brasil.',1.1)]


def test_windows_synthesis_sends_text_via_stdin_and_wraps_pcm(monkeypatch):
    import base64
    from cronos import device_voice
    monkeypatch.setattr(device_voice.sys,'platform','win32')
    text='Brasília; $(não executar) "texto" é a resposta.'
    seen=[]
    class Process:
        returncode=0
        def communicate(self,input=None,timeout=None):
            assert json.loads(input)['text']==text
            return base64.b64encode(b'\0\1'*1600),None
        def poll(self):return 0
    def create(args,**kwargs):
        assert text not in str(args) and kwargs['shell'] is False
        seen.append(args);return Process()
    monkeypatch.setattr(subprocess,'Popen',create)
    audio=device_voice._render(text,1,threading.Event())
    assert audio[:4]==b'RIFF' and len(seen)==1
    with wave.open(io.BytesIO(audio),'rb') as source:assert source.getframerate()==16000


def test_windows_synthesis_cancellation_stops_child(monkeypatch):
    from cronos import device_voice
    monkeypatch.setattr(device_voice.sys,'platform','win32')
    cancelled=threading.Event();closed=[]
    class Process:
        def __init__(self):self.done=False
        def communicate(self,**kwargs):
            if self.done:return b'',None
            cancelled.set();raise subprocess.TimeoutExpired('controlled',.1)
        def poll(self):return 1 if self.done else None
        def kill(self):self.done=True;closed.append(True)
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**kw:Process())
    with pytest.raises(RuntimeError):device_voice._render('Resposta',1,cancelled)
    assert closed==[True]
