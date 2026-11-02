import asyncio
import json
from dataclasses import replace

from fastapi.testclient import TestClient

from cronos import council
from cronos.app import create_app
from cronos.providers import ProviderError
from cronos.reply_stream import deliver, deliver_intro, intro_sink, reply_sink
from test_backend import AUTH, settings


def test_all_configured_models_contribute_but_only_synthesis_is_delivered(settings, monkeypatch):
    monkeypatch.setattr('cronos.integrations.provider_catalog',lambda current:[
        {'id':'gemini','configured':True},{'id':'mistral','configured':True},{'id':'openai','configured':True}])
    calls=[];spoken=[]
    class Fake:
        def __init__(self,name):self.name=name
        async def reply(self,system,messages):
            draft='CONSELHO DE IAs' in system
            calls.append((self.name,'draft' if draft else 'synthesis',system))
            if draft:
                await deliver_intro('Rascunho não autorizado. ')
                await deliver('Rascunho não autorizado.')
                if self.name=='openai':raise ProviderError('Cota esgotada.',429)
                return {'reply':self.name+' analisou.', 'topics':[],
                        'tool_calls':[{'name':'web_search','arguments':{'query':'não executar'}}]}
            assert 'gemini analisou.' in system and 'mistral analisou.' in system
            assert 'openai analisou.' not in system
            await deliver('Resposta final única.')
            return {'reply':'Resposta final única.','topics':[],'tool_calls':[]}
    monkeypatch.setattr('cronos.conversation_transport.conversation_provider',lambda route:Fake(route.provider))
    async def run():
        async def capture(value):spoken.append(value)
        a=reply_sink.set(capture)
        b=intro_sink.set(capture)
        try:return await council.CouncilProvider(settings).reply('persona',[{'role':'user','content':'Explique Sócrates'}])
        finally:reply_sink.reset(a);intro_sink.reset(b)
    result=asyncio.run(run())
    assert [name for name,kind,_ in calls if kind=='draft']==['gemini','mistral','openai']
    assert [name for name,kind,_ in calls if kind=='synthesis']==['gemini']
    assert spoken==['Resposta final única.']
    assert result['council']=={'attempted':['gemini','mistral','openai'],
                                'contributed':['gemini','mistral'],'failed':['openai'],'synthesizer':'gemini'}
    assert result['provider_calls']==4 and result['tool_calls']==[]


def test_slow_contributor_is_bounded_and_reported(settings, monkeypatch):
    monkeypatch.setattr(council,'CONTRIBUTION_TIMEOUT_SECONDS',.02)
    monkeypatch.setattr('cronos.integrations.provider_catalog',lambda current:[
        {'id':'gemini','configured':True},{'id':'slow','configured':True}])
    class Fake:
        def __init__(self,name):self.name=name
        async def reply(self,system,messages):
            if 'CONSELHO DE IAs' in system:
                if self.name=='slow':await asyncio.sleep(1)
                return {'reply':'análise rápida','topics':[],'tool_calls':[]}
            return {'reply':'Resposta pronta.','topics':[],'tool_calls':[]}
    monkeypatch.setattr('cronos.conversation_transport.conversation_provider',lambda route:Fake(route.provider))
    result=asyncio.run(council.CouncilProvider(settings).reply('persona',[{'role':'user','content':'pergunta'}]))
    assert result['council']['failed']==['slow']
    assert result['reply']=='Resposta pronta.'


def test_chat_reports_real_council_and_voice_uses_text_route(settings, monkeypatch):
    catalog=lambda current:[
        {'id':'gemini','configured':True,'model':'test'}, {'id':'other','configured':True,'model':'test'}]
    monkeypatch.setattr('cronos.integrations.provider_catalog',catalog)
    monkeypatch.setattr('cronos.app.provider_catalog',catalog)
    class Fake:
        def __init__(self,name):self.name=name
        async def reply(self,system,messages):
            if 'CONSELHO DE IAs' in system:
                return {'reply':self.name+' examinou a pergunta.','topics':[],'tool_calls':[]}
            return {'reply':'Resposta conjunta e coerente.','topics':[],'tool_calls':[]}
    monkeypatch.setattr('cronos.conversation_transport.conversation_provider',lambda route:Fake(route.provider))
    with TestClient(create_app(replace(settings,direct_audio_chat=True,gemini_transport='live'))) as client:
        status=client.get('/status',headers=AUTH).json()
        assert status['council_enabled'] and not status['direct_audio_chat']
        for question in ('Explique a filosofia antiga.','Oi Cronos'):
            response=client.post('/chat/stream',headers=AUTH,json={'message':question})
            result=json.loads(response.text.splitlines()[-1])['result']
            assert result['council']['contributed']==['gemini','other']
            assert result['reply']=='Resposta conjunta e coerente.'
            assert result['timings_ms']['provider_calls']==3
