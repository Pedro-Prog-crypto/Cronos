import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from cronos.app import create_app
from cronos.config import Settings
from cronos.memory import Memory
from cronos.monitor import Monitor
from cronos.providers import ProviderError

AUTH = {'Authorization': 'Bearer ' + 'a'*32}


@pytest.fixture
def monitor(tmp_path, monkeypatch):
    personality=tmp_path/'personality.md'
    personality.write_text('Personality private content')
    settings=replace(Settings.from_env(),token='a'*32,vault=tmp_path/'vault',personality=personality,
                     gemini_key='PRIVATE_KEY', providers_file=tmp_path/'providers.json')
    monkeypatch.setattr('cronos.monitor.memory_pressure',lambda:35)
    monkeypatch.setattr('cronos.monitor.shutil.disk_usage',lambda path:SimpleNamespace(free=1024**3))
    return Monitor(settings,Memory(settings.vault))


def test_baseline_change_and_recovery_deduplicates(monitor):
    monitor.collect()
    assert monitor.snapshot()['alerts']==[]
    monitor.settings.personality.write_text('Changed private text')
    monitor.collect(); monitor.collect()
    result=monitor.snapshot()
    assert [alert['code'] for alert in result['alerts']]==['personality_changed']
    assert len(result['events'])==1
    monitor.settings.personality.write_text('Personality private content')
    monitor.collect()
    assert monitor.snapshot()['events'][-1]['status']=='resolved'
    assert not monitor.snapshot()['alerts']


def test_resources_and_export_alerts_no_private_data(monitor, monkeypatch):
    monkeypatch.setattr('cronos.monitor.memory_pressure',lambda:95)
    monkeypatch.setattr('cronos.monitor.shutil.disk_usage',lambda path:SimpleNamespace(free=100*1024**2))
    with monitor.memory.connect() as db:
        db.execute("INSERT INTO exports(path,marker,header,body) VALUES('x','test','h','PRIVATE_NOTE')")
    monitor.collect()
    result=monitor.snapshot()
    assert {'ram','disk','exports'}=={alert['code'] for alert in result['alerts']}
    assert result['resources']['disk_free_mib']==100
    serialized=json.dumps(result)
    for private in ('PRIVATE_KEY','PRIVATE_NOTE','Personality private content',str(monitor.settings.vault)):
        assert private not in serialized


def test_missing_personality_and_read_failure_are_critical(monitor):
    monitor.settings.personality.unlink()
    monitor.memory.database.unlink()
    monitor.collect()
    assert {'personality_unavailable','memory_check'}=={alert['code'] for alert in monitor.snapshot()['alerts']}
    assert all(alert['severity']=='critical' for alert in monitor.snapshot()['alerts'])
    assert not monitor.memory.database.exists() # read-only check never creates a replacement DB


def test_denials_expire_and_do_not_claim_hacker(monitor, monkeypatch):
    now=[100]
    monkeypatch.setattr('cronos.monitor.time.monotonic',lambda:now[0])
    for _ in range(4): monitor.denied()
    assert not monitor.snapshot()['alerts']
    monitor.denied()
    assert monitor.snapshot()['alerts'][0]['code']=='access_denied'
    assert 'não comprova invasão' in monitor.snapshot()['alerts'][0]['suggestion']
    now[0]=161; monitor.collect()
    assert not monitor.snapshot()['alerts']


def test_acknowledgement_not_resolution_and_ring_bound(monitor):
    monitor.response('/chat',503)
    alert=monitor.snapshot()['alerts'][0]
    assert monitor.acknowledge(alert['id'])
    assert monitor.snapshot()['alerts'][0]['acknowledged']
    monitor.response('/chat',200)
    assert not monitor.snapshot()['alerts']
    assert not monitor.acknowledge(alert['id'])
    for _ in range(110):
        monitor.response('/chat',503); monitor.response('/chat',200)
    result=monitor.snapshot()
    assert len(result['events'])==200
    assert len(monitor.snapshot(result['cursor']-1)['events'])==1


def test_authenticated_api_immediate_errors_and_recovery(monitor):
    class Provider:
        fail=True
        async def reply(self,*args):
            if self.fail: raise ProviderError('PRIVATE_PROVIDER_ERROR')
            return {'reply':'ok','topics':[]}
    provider=Provider()
    with TestClient(create_app(monitor.settings,provider)) as client:
        assert client.get('/monitor').status_code==401
        for _ in range(4): client.get('/status',headers={'Authorization':'Bearer wrong'})
        result=client.get('/monitor',headers=AUTH).json()
        assert 'access_denied' in {alert['code'] for alert in result['alerts']}
        assert client.post('/chat',headers=AUTH,json={'message':'Private question'}).status_code==503
        result=client.get('/monitor',headers=AUTH).json()
        alert=next(alert for alert in result['alerts'] if alert['code']=='service_conversation')
        assert 'PRIVATE_PROVIDER_ERROR' not in json.dumps(result)
        assert client.post(f"/monitor/alerts/{alert['id']}/ack",headers=AUTH).status_code==200
        provider.fail=False
        assert client.post('/chat',headers=AUTH,json={'message':'Private question'}).status_code==200
        result=client.get('/monitor',headers=AUTH).json()
        assert 'service_conversation' not in {alert['code'] for alert in result['alerts']}
        assert client.get('/monitor?after=-1',headers=AUTH).status_code==422
        assert client.post('/monitor/alerts/999/ack',headers=AUTH).status_code==404


def test_periodic_monitor_really_checks_and_cancels(monitor):
    async def scenario():
        monitor.interval=.01
        task=asyncio.create_task(monitor.run())
        await asyncio.sleep(.05)
        assert monitor.checked_at is not None
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
    asyncio.run(scenario())


def test_monitor_does_not_contact_providers(monitor, monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('diagnostic must not call model APIs')
    monkeypatch.setattr('httpx.AsyncClient',forbidden)
    monitor.collect()
    assert monitor.snapshot()['state']=='monitoring'


def test_assistant_reads_real_diagnostics_through_tool(monitor):
    class Provider:
        calls=0
        async def reply(self,system,messages):
            self.calls+=1
            if self.calls==1:
                assert 'system_diagnostics' in system
                return {'reply':'Vou consultar o diagnóstico.','topics':[],
                        'tool_calls':[{'name':'system_diagnostics','arguments':{}}]}
            results=json.loads(messages[-1]['content'].split('\n',1)[1])
            data=results[0]['result']
            assert data['checked_at'] is not None
            assert data['resources']['ram_used_percent']==35
            assert 'Não é antivírus' in data['scope']
            assert 'events' not in data
            return {'reply':'O radar informa 35% de RAM em uso, dentro do seu escopo limitado.','topics':[]}
    with TestClient(create_app(monitor.settings,Provider())) as client:
        result=client.post('/chat',headers=AUTH,json={'message':'Como está o diagnóstico?'}).json()
        assert result['tool_results'][0]['name']=='system_diagnostics'
        assert result['tool_results'][0]['status']=='completed'
