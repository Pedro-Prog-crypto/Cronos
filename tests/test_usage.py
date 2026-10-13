import asyncio
import json
from dataclasses import replace
import httpx
import pytest
from cronos import usage, diagnostics
from cronos.providers import Gemini,ProviderError
from test_backend import settings
from fastapi.testclient import TestClient
from cronos.app import create_app

def test_pause_survives_new_provider_and_cleared_memory(settings,monkeypatch):
    calls=[];client=httpx.AsyncClient
    def respond(request):
        calls.append(request)
        return httpx.Response(429,json={'error':{'message':'private secret prompt'}},headers={'Retry-After':'3600'})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:client(transport=httpx.MockTransport(respond),**kw))
    settings=replace(settings,gemini_key='private-test-key')
    async def run():
        with usage.request_scope('conversation','test-turn'):
            with pytest.raises(ProviderError,match='429'):await Gemini(settings).reply('private personality',[{'role':'user','content':'private question'}])
        Gemini.cooldowns.clear() # simulate losing process memory when restarting
        with pytest.raises(ProviderError,match='Nenhuma nova chamada'):await Gemini(settings).reply('private personality',[{'role':'user','content':'private question'}])
    asyncio.run(run());assert len(calls)==1
    log=(usage.ROOT/'gemini-requests.jsonl').read_text()
    assert json.loads(log)['source']=='conversation'
    assert all(value not in log for value in ('private-test-key','private question','private personality','private secret'))

def test_local_diagnostic_never_instantiates_provider(settings,monkeypatch,capsys):
    monkeypatch.setattr(diagnostics,'load_dotenv',lambda *a,**k:None)
    monkeypatch.setattr(diagnostics.Settings,'from_env',lambda:settings)
    def forbidden(*a,**kw):raise AssertionError('A local diagnostic must not call the provider')
    monkeypatch.setattr(diagnostics,'make_provider',forbidden)
    diagnostics.main([])
    assert 'Nenhuma chamada à IA foi enviada' in capsys.readouterr().out

def test_successful_generation_records_usage_counts_not_content(settings,monkeypatch):
    client=httpx.AsyncClient
    response={'candidates':[{'content':{'parts':[{'text':json.dumps({'reply':'private reply','topics':[]})}]}}],
              'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':12,'totalTokenCount':112,'private':'secret'}}
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=response)),**kw))
    asyncio.run(Gemini(replace(settings,gemini_key='secret-key')).reply('secret prompt',[{'role':'user','content':'secret question'}]))
    row=json.loads((usage.ROOT/'gemini-requests.jsonl').read_text())
    assert row['totalTokenCount']==112 and row['http']==200
    assert 'secret' not in json.dumps(row) and 'private reply' not in json.dumps(row)

def test_startup_and_background_queries_do_not_generate_and_plain_chat_calls_once(settings):
    class Provider:
        calls=0
        async def reply(self,*args):
            self.calls+=1
            return {'reply':'Resposta de teste','topics':[],'tool_calls':[]}
    provider=Provider();headers={'Authorization':'Bearer test-token'}
    with TestClient(create_app(settings,provider)) as client:
        for _ in range(3):
            for path in ('/status','/monitor','/modules','/memory/graph'):
                assert client.get(path,headers=headers).status_code==200
            assert client.post('/memory/sync',headers=headers).status_code==200
        assert provider.calls==0
        assert client.post('/chat',headers=headers,json={'message':'Olá'}).status_code==200
        assert provider.calls==1
