"""Contract tests against the Brain Cloud 0.4.4 API shape, without credentials."""
import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from cronos.brain_cloud import BrainCloud, local_action
from cronos.engine import Engine
from cronos.storage import Memory
from cronos.providers import ProviderError
from cronos.app import create_app
from fastapi.testclient import TestClient
from dataclasses import replace
from test_backend import settings, AUTH


def pairing(vault, url='http://127.0.0.1:8787'):
    path = vault / '.cronos' / 'brain-cloud.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    device = str(uuid4())
    path.write_text(json.dumps({'baseUrl':url, 'deviceId':device, 'credential':'a'*64}))
    return path


def mock_client(monkeypatch, handler):
    original = httpx.AsyncClient
    def factory(*args, **kwargs):
        return original(*args, transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(httpx, 'AsyncClient', factory)


def test_brain_receives_question_remembers_and_resumes_remote_conversation(tmp_path, monkeypatch):
    pairing(tmp_path)
    remote = str(uuid4()); local = uuid4(); bodies=[]
    def handler(request):
        if request.url.path == '/v1/auth/sessions':
            assert json.loads(request.content)['credential'] == 'a'*64
            return httpx.Response(201, json={'accessToken':'private-session','expiresIn':900})
        assert request.url.path == '/v1/chat'
        assert request.headers['authorization'] == 'Bearer private-session'
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={'conversationId':remote,'text':'Boa resposta, senhor.', 'status':'completed','warnings':[]})
    mock_client(monkeypatch, handler)
    assert asyncio.run(BrainCloud(tmp_path).chat(local, 'Explique filosofia.'))['text'] == 'Boa resposta, senhor.'
    assert asyncio.run(BrainCloud(tmp_path).chat(local, 'Continue, por favor.'))['text'] == 'Boa resposta, senhor.'
    assert bodies == [
        {'message':'Explique filosofia.','remember':True},
        {'message':'Continue, por favor.','remember':True,'conversationId':remote},
    ]


def test_brain_failure_does_not_claim_a_saved_answer(tmp_path, monkeypatch):
    pairing(tmp_path)
    def handler(request):
        if request.url.path == '/v1/auth/sessions':return httpx.Response(201,json={'accessToken':'session','expiresIn':900})
        return httpx.Response(503,json={'error':{'code':'no_available_model'}})
    mock_client(monkeypatch, handler)
    brain=BrainCloud(tmp_path)
    with pytest.raises(ProviderError, match='no_available_model'):
        asyncio.run(brain.chat(uuid4(), 'Quem foi Sócrates?'))
    assert not list((tmp_path/'.cronos').glob('brain-sessions-*.json'))


def test_pairing_export_authenticates_and_heartbeat_reports_presence(tmp_path, monkeypatch):
    from tools.connect_brain_cloud import import_pairing
    exported=tmp_path/'cronos-desktop.json'
    exported.write_text(json.dumps({'baseUrl':'http://127.0.0.1:8787', 'deviceId':str(uuid4()), 'credential':'a'*64}))
    calls=[]
    def handler(request):
        calls.append(request.url.path)
        if request.url.path=='/v1/health':return httpx.Response(200,json={'name':'CRONOS BRAIN CLOUD','status':'ok'})
        if request.url.path=='/v1/auth/sessions':return httpx.Response(201,json={'accessToken':'session','expiresIn':900})
        if request.url.path=='/v1/devices/heartbeat':
            assert request.headers['authorization']=='Bearer session'
            return httpx.Response(200,json={'connected':True})
        raise AssertionError('Unexpected request')
    mock_client(monkeypatch,handler)
    vault=tmp_path/'vault'
    saved=import_pairing(exported,vault)
    assert saved==vault/'.cronos'/'brain-cloud.json'
    assert asyncio.run(BrainCloud(vault).heartbeat()) is True
    assert calls==['/v1/health','/v1/auth/sessions','/v1/auth/sessions','/v1/devices/heartbeat']


def test_brain_rejects_insecure_remote_and_keeps_desktop_actions_local():
    with pytest.raises(ValueError,match='HTTPS'):
        BrainCloud.validate({'baseUrl':'http://brain.example','deviceId':str(uuid4()),'credential':'a'*64})
    assert local_action('Cronos, abra minha música')
    assert local_action('Leia esta tela')
    assert not local_action('Quem foi Sócrates?')


def test_engine_uses_brain_for_reasoning_without_local_model(settings, monkeypatch):
    pairing(settings.vault)
    remote=str(uuid4())
    async def answer(self, session, message):
        assert message=='Explique a Primeira Guerra Mundial.'
        return {'conversationId':remote,'text':'A guerra começou em 1914, senhor.', 'status':'completed','warnings':[]}
    monkeypatch.setattr(BrainCloud, 'chat', answer)
    memory=Memory(settings.vault)
    session=uuid4()
    result=asyncio.run(Engine(settings,memory,None).chat(session,'Explique a Primeira Guerra Mundial.'))
    assert result['provider_used']=='brain-cloud'
    assert '1914' in result['reply']
    assert result['notes']==[]
    assert len(memory.history(session))==2


def test_unavailable_brain_falls_back_to_local_answer_with_visible_warning(settings, monkeypatch):
    pairing(settings.vault)
    async def unavailable(self, session, message):
        raise ProviderError('Brain sem modelo', 503)
    class Local:
        async def reply(self, system, messages):
            return {'reply':'Resposta local confirmada.', 'topics':[], 'tool_calls':[]}
    monkeypatch.setattr(BrainCloud, 'chat', unavailable)
    monkeypatch.setattr('cronos.conversation_transport.conversation_provider', lambda _:Local())
    memory=Memory(settings.vault)
    result=asyncio.run(Engine(settings,memory,type('Tools',(),{'tools':{},'catalog':lambda _:[]})()).chat(uuid4(),'Quem foi Sócrates?'))
    assert result['reply']=='Resposta local confirmada.'
    assert result['fallback_used'] is True
    assert 'Brain Cloud indisponível' in result['warnings'][0]


def test_pairing_disables_direct_gemini_audio_only_when_online(settings):
    pairing(settings.vault)
    configured=replace(settings, direct_audio_chat=True, gemini_key='fixture', gemini_transport='live')
    with TestClient(create_app(configured)) as client:
        status=client.get('/status',headers=AUTH).json()
        assert status['brain_cloud_active'] and not status['direct_audio_chat']
    with TestClient(create_app(replace(configured,privacy_mode='local'))) as client:
        status=client.get('/status',headers=AUTH).json()
        assert not status['brain_cloud_active']
