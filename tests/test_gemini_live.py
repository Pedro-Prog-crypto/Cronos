import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace as NS
import pytest
from cronos import gemini_live,usage
from cronos.providers import Gemini,ProviderError
from cronos.app import create_app
from fastapi.testclient import TestClient
from test_backend import settings
from cronos.config import Settings

def test_default_configuration_uses_original_live_model(monkeypatch):
    monkeypatch.delenv('GEMINI_TRANSPORT',raising=False)
    monkeypatch.delenv('GEMINI_LIVE_MODEL',raising=False)
    settings=Settings.from_env()
    assert settings.gemini_transport=='live'
    assert settings.gemini_live_model==gemini_live.ORIGINAL_MODELS[0]

def test_live_respects_local_privacy_mode(settings,monkeypatch):
    def forbidden(*args):raise AssertionError('Local mode cannot connect')
    monkeypatch.setattr(gemini_live,'make_client',forbidden)
    with pytest.raises(ProviderError,match='Modo local'):
        asyncio.run(Gemini(replace(settings,gemini_key='dummy-key',privacy_mode='local',gemini_transport='live')).reply('persona',[]))

def test_live_uses_original_protocol_preserves_persona_history_and_closes(settings,monkeypatch):
    sent=[];configs=[];closed=[]
    raw=json.dumps({'reply':'Resposta com personalidade','topics':[],'tool_calls':[]})
    class Session:
        async def send_client_content(self,**kwargs):sent.append(kwargs)
        async def receive(self):
            yield NS(server_content=NS(output_transcription=NS(text=raw[:20]),turn_complete=False))
            yield NS(server_content=NS(output_transcription=NS(text=raw[20:]),turn_complete=True))
    class Connection:
        async def __aenter__(self):return Session()
        async def __aexit__(self,*args):closed.append('session')
    class Aio:
        live=None
        def __init__(self):self.live=self
        def connect(self,**kwargs):configs.append(kwargs);return Connection()
        async def aclose(self):closed.append('client')
    monkeypatch.setattr(gemini_live,'make_client',lambda key:NS(aio=Aio()))
    result=asyncio.run(Gemini(replace(settings,gemini_key='private-key',gemini_transport='live')).reply('PERSONALIDADE EXATA',[{'role':'user','content':'antiga'},{'role':'assistant','content':'resposta antiga'},{'role':'user','content':'nova'}]))
    assert result['reply']=='Resposta com personalidade'
    assert configs[0]['model']==gemini_live.ORIGINAL_MODELS[0]
    assert configs[0]['config'].response_modalities==['AUDIO']
    assert configs[0]['config'].system_instruction.startswith('PERSONALIDADE EXATA\n')
    assert [t['role'] for t in sent[0]['turns']]==['user','model','user']
    assert sent[0]['turn_complete'] is True and closed==['session','client']

def test_rest_pause_does_not_block_live_and_only_original_fallback_is_tried(settings,monkeypatch):
    import hashlib
    key='dummy-key';identity=hashlib.sha256((key+'|'+settings.gemini_model).encode()).hexdigest();usage.pause(identity,3600)
    calls=[];closed=[]
    class Client:
        def __init__(self):self.aio=self
        async def aclose(self):closed.append(True)
    monkeypatch.setattr(gemini_live,'make_client',lambda key:Client())
    async def turn(client,model,*args):
        calls.append(model)
        if len(calls)==1:raise RuntimeError('503 UNAVAILABLE private-key')
        return {'reply':'ok','topics':[],'tool_calls':[]}
    monkeypatch.setattr(gemini_live,'turn',turn)
    result=asyncio.run(Gemini(replace(settings,gemini_key=key,gemini_transport='live')).reply('persona',[{'role':'user','content':'hello'}]))
    assert result['reply']=='ok' and calls==list(gemini_live.ORIGINAL_MODELS) and len(closed)==2

def test_live_quota_is_not_retried_and_error_body_is_private(settings,monkeypatch):
    calls=[]
    class Client:
        def __init__(self):self.aio=self
        async def aclose(self):pass
    monkeypatch.setattr(gemini_live,'make_client',lambda key:Client())
    async def turn(*args):calls.append(True);raise RuntimeError('RESOURCE_EXHAUSTED quota private-key private-prompt')
    monkeypatch.setattr(gemini_live,'turn',turn)
    provider=Gemini(replace(settings,gemini_key='dummy-key',gemini_transport='live'))
    async def run():
        for _ in range(2):
            with pytest.raises(ProviderError) as error:await provider.reply('persona',[{'role':'user','content':'hello'}])
            assert error.value.status==429 and 'private' not in str(error.value)
    asyncio.run(run());assert len(calls)==1


def test_live_timeouts_are_bounded_across_model_routes(settings,monkeypatch):
    calls=[]
    class Client:
        def __init__(self):self.aio=self
        async def aclose(self):pass
    monkeypatch.setattr(gemini_live,'make_client',lambda key:Client())
    monkeypatch.setattr(gemini_live,'LIVE_ATTEMPT_TIMEOUT_SECONDS',0.01)
    monkeypatch.setattr(gemini_live,'LIVE_TOTAL_TIMEOUT_SECONDS',0.03)
    async def slow_turn(client,model,*args):calls.append(model);await asyncio.sleep(1)
    monkeypatch.setattr(gemini_live,'turn',slow_turn)
    started=__import__('time').monotonic()
    with pytest.raises(ProviderError,match='demorou demais'):
        asyncio.run(gemini_live.reply(replace(settings,gemini_key='test'),'',[]))
    assert calls==list(gemini_live.ORIGINAL_MODELS)
    assert __import__('time').monotonic()-started<0.2

def test_provider_429_is_not_disguised_as_backend_503(settings):
    class Provider:
        async def reply(self,*args):raise ProviderError('Limite do provedor',429)
    with TestClient(create_app(settings,Provider())) as client:
        response=client.post('/chat',headers={'Authorization':'Bearer test-token'},json={'message':'Olá'})
        assert response.status_code==429

def test_429_after_tool_preserves_results_and_status(settings):
    class Provider:
        calls=0
        async def reply(self,*args):
            self.calls+=1
            if self.calls==1:return {'reply':'Consultando','topics':[],'tool_calls':[{'name':'obsidian_search','arguments':{'query':'Platão'}}]}
            raise ProviderError('Limite do provedor',429)
    with TestClient(create_app(settings,Provider())) as client:
        response=client.post('/chat',headers={'Authorization':'Bearer test-token'},json={'message':'Procure Platão nas notas'})
        assert response.status_code==429 and response.json()['detail']['tool_results']

def test_live_returns_full_valid_json_without_waiting_for_discarded_audio(settings,monkeypatch):
    closed=[]
    raw=json.dumps({'reply':'Resposta completa','topics':[{'title':'Platão','summary':'Registro completo'}],
                    'tool_calls':[{'name':'obsidian_search','arguments':{'query':'Platão'}}]})
    class Session:
        async def send_client_content(self,**kwargs):pass
        async def receive(self):
            yield NS(server_content=NS(output_transcription=NS(text=raw[:30]),turn_complete=False))
            yield NS(server_content=NS(output_transcription=NS(text=raw[30:]),turn_complete=False))
            raise AssertionError('Discarded Gemini audio must not delay a validated response')
    class Connection:
        async def __aenter__(self):return Session()
        async def __aexit__(self,*args):closed.append(True)
    class Client:
        def __init__(self):self.aio=self;self.live=self
        def connect(self,**kwargs):return Connection()
        async def aclose(self):pass
    monkeypatch.setattr(gemini_live,'make_client',lambda key:Client())
    result=asyncio.run(Gemini(replace(settings,gemini_transport='live',gemini_key='test')).reply('persona',[{'role':'user','content':'Pergunta'}]))
    assert result['reply']=='Resposta completa' and result['topics'][0]['title']=='Platão'
    assert result['tool_calls'][0]['arguments']=={'query':'Platão'} and closed==[True]


def test_live_does_not_return_early_for_incomplete_json(settings,monkeypatch):
    raw='{"reply":"Texto com } e \\\" aspas","topics":[],"tool_calls":[]}'
    class Session:
        async def send_client_content(self,**kw):pass
        async def receive(self):
            yield NS(server_content=NS(output_transcription=NS(text=raw[:20]),turn_complete=False))
            yield NS(server_content=NS(output_transcription=NS(text=raw[20:]),turn_complete=True))
    class Connection:
        async def __aenter__(self):return Session()
        async def __aexit__(self,*args):pass
    client=NS(aio=NS(live=NS(connect=lambda **kwargs:Connection())))
    result=asyncio.run(gemini_live.turn(client,settings.gemini_live_model,'persona',[{'role':'user','content':'Pergunta'}]))
    assert result['reply']=='Texto com } e " aspas'


@pytest.mark.parametrize('finished',[True,False])
def test_live_natural_language_only_after_server_turn_complete(settings,finished):
    text='Podemos estudar filosofia usando exemplos do cotidiano.'
    class Session:
        async def send_client_content(self,**kwargs):pass
        async def receive(self):
            yield NS(server_content=NS(output_transcription=NS(text=text),turn_complete=finished))
    class Connection:
        async def __aenter__(self):return Session()
        async def __aexit__(self,*args):pass
    client=NS(aio=NS(live=NS(connect=lambda **kwargs:Connection())))
    if finished:
        result=asyncio.run(gemini_live.turn(client,settings.gemini_live_model,'persona',[{'role':'user','content':'Explique'}]))
        assert result=={'reply':text,'topics':[],'tool_calls':[]}
    else:
        with pytest.raises(ProviderError):asyncio.run(gemini_live.turn(client,settings.gemini_live_model,'persona',[{'role':'user','content':'Explique'}]))
