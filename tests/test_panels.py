import asyncio
import json
from dataclasses import replace
from uuid import uuid4
from zipfile import ZipFile

import httpx
import pytest
from fastapi.testclient import TestClient
from cronos.app import create_app
from cronos.config import Settings
from cronos.tools import Tool, Arguments

AUTH={'Authorization':'Bearer '+'p'*32}

@pytest.fixture
def settings(tmp_path):
    personality=tmp_path/'personality.md';personality.write_text('Personalidade preservada.')
    files=tmp_path/'files';files.mkdir()
    return Settings(tmp_path/'vault',personality,'p'*32,'gemini','private-gemini','gemini-2.5-flash',
                    'private-fish','voice-original','s1','http://127.0.0.1:11434','gemma3:4b',
                    files_root=files,providers_file=tmp_path/'config/providers.json')


def test_panel_preferences_are_private_validated_persisted_and_applied(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get('/panels').status_code==401
        result=client.get('/panels',headers=AUTH)
        assert result.status_code==200
        assert 'private-gemini' not in result.text and 'private-fish' not in result.text
        assert len(result.json()['modules'])==12
        assert result.json()['cpu_percent'] is None
        for payload in ({'voice_speed':4},{'context_messages':0},{'GEMINI_API_KEY':'forbidden'},{'confirm_critical':False}):
            assert client.patch('/panels/preferences',json=payload,headers=AUTH).status_code==422
        r=client.patch('/panels/preferences',json={'voice_speed':1.3,'context_messages':12,'response_style':'concise','save_diary':False},headers=AUTH)
        assert r.status_code==200
        assert client.app.state.engine.settings.context_messages==12
        assert client.app.state.engine.settings.gemini_key==settings.gemini_key
        assert client.app.state.engine.settings.gemini_live_model==settings.gemini_live_model
        session=uuid4();client.app.state.memory.record(session,'Cronos, na escuta?','Estou na escuta.',[])
        assert not (settings.vault/'Conversas'/f'{session}.md').exists()
        assert len(client.app.state.memory.history(session))==2
    with TestClient(create_app(settings)) as client:
        assert client.get('/panels',headers=AUTH).json()['preferences']['context_messages']==12
        assert client.app.state.memory.save_diary is False


def test_permissions_enforced_and_revocation_cancels_pending_action(settings):
    with TestClient(create_app(settings)) as client:
        registry=client.app.state.registry
        calls=[];registry.register(Tool('files_custom','custom',Arguments,lambda args:calls.append(True)))
        client.patch('/panels/preferences',json={'confirm_tools':True},headers=AUTH)
        r=client.post('/tools/execute',json={'name':'files_custom','arguments':{}},headers=AUTH).json()
        assert r['status']=='pending_confirmation' and not calls
        client.patch('/panels/preferences',json={'files_enabled':False},headers=AUTH)
        denied=client.post('/tools/approvals/'+r['approval_id'],json={'session_id':r['session_id'],'accepted':True},headers=AUTH).json()
        assert denied['status']=='failed' and not calls
        denied=client.post('/tools/execute',json={'name':'files_list','arguments':{}},headers=AUTH).json()
        assert denied['status']=='failed'


def test_backup_uses_consistent_sqlite_and_only_markdown(settings):
    with TestClient(create_app(settings)) as client:
        (settings.vault/'Temas'/'Platao.md').write_text('# Platão\nTexto de teste.')
        (settings.vault/'.env').write_text('SECRET=must-not-backup')
        client.post('/memory/sync',headers=AUTH)
        r=client.post('/panels/backup',headers=AUTH)
        assert r.status_code==200
        archive=settings.vault/'.cronos/backups'/r.json()['name']
        with ZipFile(archive) as z:
            assert 'Temas/Platao.md' in z.namelist()
            assert '.cronos/memory.sqlite3' in z.namelist()
            assert '.env' not in z.namelist()
            assert not any('backups' in n for n in z.namelist())
        assert client.get('/panels',headers=AUTH).json()['backup']['name']==r.json()['name']
        assert not list(archive.parent.glob('*.tmp'))


def test_plan_controls_and_registration_do_not_switch_working_provider(settings):
    with TestClient(create_app(settings)) as client:
        r=client.post('/missions',json={'objective':'Estudar Platão','steps':['Ler','Escrever']},headers=AUTH).json()
        plan=r['plan'];plan.update(priority='high',due_date='2026-12-01',review=False)
        plan['steps'][0].update(status='completed',due_date='2026-11-01')
        r=client.patch('/missions/'+r['id'],json=plan,headers=AUTH)
        assert r.status_code==200 and r.json()['plan']['steps'][0]['done'] is True
        spec={'id':'new-provider','kind':'openai','model':'example','base_url':'https://example.org/v1','key_env':'NEW_PROVIDER_KEY'}
        assert client.post('/panels/adapters',json={'spec':spec},headers=AUTH).status_code==200
        assert client.app.state.engine.settings.provider=='gemini'
        assert client.post('/panels/adapters',json={'spec':spec},headers=AUTH).status_code==422
        spec.update(id='bad',base_url='http://example.org')
        assert client.post('/panels/adapters',json={'spec':spec},headers=AUTH).status_code==422


def test_network_is_an_explicit_probe_not_a_model_call(settings,monkeypatch):
    requests=[];original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(lambda r:(requests.append(str(r.url)) or httpx.Response(204)))))
    with TestClient(create_app(settings)) as client:
        assert client.get('/panels',headers=AUTH).json()['network'] is None and not requests
        result=client.post('/panels/network',headers=AUTH)
        assert result.json()['connected'] is True
        assert requests==['https://www.gstatic.com/generate_204']
        assert client.get('/panels',headers=AUTH).json()['network']['connected'] is True


def test_vault_picker_only_changes_vault_setting_after_explicit_selection(settings,tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    env=tmp_path/'.env';env.write_text('GEMINI_API_KEY="keep-gemini"\nFISH_API_KEY="keep-fish"\n')
    selected=tmp_path/'selected-vault';selected.mkdir()
    with TestClient(create_app(settings,windows_platform='win32')) as client:
        assert client.post('/panels/vault',json={'path':str(selected)},headers=AUTH).json()['restart_required']
        assert 'GEMINI_API_KEY="keep-gemini"' in env.read_text()
        assert 'FISH_API_KEY="keep-fish"' in env.read_text()
        assert client.app.state.memory.vault==settings.vault
        assert client.app.state.engine.settings.gemini_live_model==settings.gemini_live_model
        assert client.post('/panels/vault',json={'path':'relative-folder'},headers=AUTH).status_code==422


def test_retention_archives_old_backups_without_deleting_notes(settings):
    import os,time
    with TestClient(create_app(settings)) as client:
        r=client.post('/panels/backup',headers=AUTH).json()
        root=settings.vault/'.cronos/backups'
        os.utime(root/r['name'],(time.time()-100*86400,time.time()-100*86400))
        assert client.patch('/panels/preferences',json={'retention_days':30},headers=AUTH).status_code==200
        assert (root/'archive'/r['name']).is_file()
        assert not (root/r['name']).exists()
        assert client.get('/panels',headers=AUTH).json()['archived_backups']==1
