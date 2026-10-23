import asyncio
import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from cronos.config import Settings
from cronos.providers import ProviderError
from cronos import evolution
from cronos.app import create_app
from cronos.memory import Memory
from cronos.tools import create_registry


def setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('SECOND_KEY','dummy')
    settings = replace(Settings.from_env(), token='test', providers_file=tmp_path/'config/providers.json',
                       vault=tmp_path/'vault', provider='gemini', gemini_key='dummy')
    settings.providers_file.parent.mkdir()
    settings.providers_file.write_text(json.dumps({'providers':[{'id':'second','kind':'openai','model':'test','base_url':'https://example.org/v1','key_env':'SECOND_KEY'}]}))
    return settings


def test_confirmation_and_reversible_routing(tmp_path, monkeypatch):
    settings=setup(tmp_path,monkeypatch)
    registry=create_registry(settings,Memory(settings.vault))
    outcome=asyncio.run(registry.execute('integrations_routing',{'enabled':True,'fallbacks':['second','second']},'session'))
    assert outcome['status']=='pending_confirmation'
    assert evolution.read(settings)['routing']['enabled']
    result=asyncio.run(registry.resolve(outcome['approval_id'],True,'session'))
    assert result['status']=='completed'
    assert evolution.read(settings)['routing']=={'enabled':True,'fallbacks':['second']}
    evolution.rollback(settings)
    assert evolution.read(settings)['routing']['enabled']
    with pytest.raises(ValueError):evolution.routing(settings,{'enabled':True,'fallbacks':['unknown']})


def test_default_fallback_uses_configured_alternative_after_transient_error(tmp_path,monkeypatch):
    settings=setup(tmp_path,monkeypatch)
    calls=[]
    class Primary:
        async def reply(self,*args):raise ProviderError('quota',429)
    class Alternative:
        async def reply(self,*args):calls.append(1);return {'reply':'ok','topics':[],'tool_calls':[]}
    def factory(settings):
        if settings.provider=='ollama':raise ProviderError('Ollama offline',503)
        return Alternative()
    monkeypatch.setattr('cronos.providers.make_provider',factory)
    wrapped=evolution.ResilientProvider(settings,Primary())
    assert evolution.read(settings)['routing']=={'enabled':True,'fallbacks':['ollama','second']}
    result=asyncio.run(wrapped.reply('system',[{'role':'user','content':'test'}]))
    assert result['provider_used']=='second' and len(calls)==1
    with pytest.raises(ProviderError):asyncio.run(wrapped.reply('system',[{'audio_pcm':b'pcm'}]))
    class Invalid:
        async def reply(self,*args):raise ProviderError('format invalid')
    with pytest.raises(ProviderError):asyncio.run(evolution.ResilientProvider(settings,Invalid()).reply('',[]))
    assert len(calls)==1


def test_slow_primary_is_bounded_and_uses_configured_reserve(tmp_path,monkeypatch):
    settings=setup(tmp_path,monkeypatch)
    evolution.routing(settings,{'enabled':True,'fallbacks':['second']})
    settings=replace(settings,provider_timeout=0.01)
    monkeypatch.setattr(evolution,'FALLBACK_ATTEMPT_TIMEOUT_SECONDS',0.1)
    monkeypatch.setattr(evolution,'FALLBACK_TOTAL_TIMEOUT_SECONDS',0.2)
    class Primary:
        async def reply(self,*args):await asyncio.sleep(1)
    class Alternative:
        async def reply(self,*args):return {'reply':'reserva','topics':[],'tool_calls':[]}
    monkeypatch.setattr('cronos.providers.make_provider',lambda settings:Alternative())
    result=asyncio.run(evolution.ResilientProvider(settings,Primary()).reply('',[{'role':'user','content':'teste'}]))
    assert result['reply']=='reserva' and result['fallback_used']


def test_slow_reserves_do_not_extend_total_fallback_budget(tmp_path,monkeypatch):
    settings=setup(tmp_path,monkeypatch)
    monkeypatch.setenv('THIRD_KEY','dummy')
    payload=json.loads(settings.providers_file.read_text())
    payload['providers'].append({'id':'third','kind':'openai','model':'test','base_url':'https://example.net/v1','key_env':'THIRD_KEY'})
    settings.providers_file.write_text(json.dumps(payload))
    evolution.routing(settings,{'enabled':True,'fallbacks':['second','third']})
    settings=replace(settings,provider_timeout=0.01)
    monkeypatch.setattr(evolution,'FALLBACK_ATTEMPT_TIMEOUT_SECONDS',0.02)
    monkeypatch.setattr(evolution,'FALLBACK_TOTAL_TIMEOUT_SECONDS',0.025)
    calls=[]
    class Slow:
        async def reply(self,*args):calls.append(True);await asyncio.sleep(1)
    monkeypatch.setattr('cronos.providers.make_provider',lambda settings:Slow())
    import time
    started=time.monotonic()
    with pytest.raises(ProviderError,match='demorou demais'):
        asyncio.run(evolution.ResilientProvider(settings,Slow()).reply('',[{'role':'user','content':'teste'}]))
    assert len(calls)==3 and time.monotonic()-started<0.2


def test_registration_validates_before_writing(tmp_path,monkeypatch):
    settings=setup(tmp_path,monkeypatch)
    async def listed(*args):return ['real-model']
    monkeypatch.setattr(evolution,'available_models',listed)
    spec={'id':'new','kind':'openai','model':'absent','base_url':'https://example.org/v1','key_env':'SECOND_KEY'}
    before=settings.providers_file.read_text()
    with pytest.raises(ValueError):asyncio.run(evolution.register(settings,spec))
    assert settings.providers_file.read_text()==before
    spec['model']='real-model'
    result=asyncio.run(evolution.register(settings,spec))
    assert result['registered']=='new' and not result['generation_tested']
    with pytest.raises(ValueError):asyncio.run(evolution.register(settings,spec))


def test_checkup_authenticated_and_key_never_returned(tmp_path,monkeypatch):
    settings=setup(tmp_path,monkeypatch)
    with TestClient(create_app(settings)) as client:
        assert client.get('/evolution').status_code==401
        headers={'Authorization':'Bearer test'}
        report=client.get('/evolution',headers=headers)
        assert report.status_code==200 and 'dummy' not in report.text
        assert report.json()['primary_provider']=='gemini'
        response=client.post('/evolution/credential',headers=headers,json={'provider_id':'second','key':'new-private-key'})
        assert response.status_code==200 and 'new-private-key' not in response.text
        assert 'new-private-key' in (tmp_path/'.env').read_text()
        assert 'new-private-key' not in client.get('/evolution',headers=headers).text
        assert client.post('/evolution/credential',headers=headers,json={'provider_id':'gemini','key':'no'}).status_code==422


def test_internal_data_excludes_secrets_and_reads_real_memory(tmp_path,monkeypatch):
    settings=setup(tmp_path,monkeypatch)
    memory=Memory(settings.vault)
    registry=create_registry(settings,memory)
    result=asyncio.run(registry.execute('cronos_internal_data',{'section':'overview'},'session'))
    assert result['status']=='completed'
    assert result['result']['memory']['statistics']==memory.stats()
    assert 'dummy' not in json.dumps(result)
    assert any(t['name']=='integrations_register' for t in result['result']['tools']['tools'])
    assert asyncio.run(registry.execute('cronos_internal_data',{'section':'.env'},'session'))['status']=='failed'


def test_partial_reply_never_switches_to_another_voice_answer(tmp_path,monkeypatch):
    from cronos.reply_stream import intro_sink, deliver_intro
    settings=setup(tmp_path,monkeypatch)
    evolution.routing(settings,{'enabled':True,'fallbacks':['second']})
    calls=[]
    class Partial:
        async def reply(self,*args):
            await deliver_intro('first sentence')
            raise ProviderError('connection lost',503)
    async def received(value):calls.append(value)
    async def run():
        token=intro_sink.set(received)
        try:
            with pytest.raises(ProviderError):await evolution.ResilientProvider(settings,Partial()).reply('',[])
            assert intro_sink.get() is received
        finally:intro_sink.reset(token)
    asyncio.run(run())
    assert calls==['first sentence']


def test_internal_configuration_tracks_runtime_changes(tmp_path,monkeypatch):
    settings=setup(tmp_path,monkeypatch)
    registry=create_registry(settings,Memory(settings.vault))
    registry.current_settings=lambda:replace(settings,context_messages=12)
    result=asyncio.run(registry.execute('cronos_internal_data',{'section':'configuration'},'session'))
    assert result['result']['context_messages']==12
