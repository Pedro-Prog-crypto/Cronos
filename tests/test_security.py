import asyncio
import os
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from cronos.app import create_app
from cronos.config import Settings
from cronos.memory import Memory
from cronos.security import SecurityError, SecurityMiddleware, local_endpoint, safe_path
from cronos.tools import create_registry


@pytest.fixture
def settings(tmp_path):
    return replace(Settings.from_env(), token='test-token', vault=tmp_path/'vault', files_root=tmp_path,
                   personality=tmp_path/'personality.md', providers_file=tmp_path/'providers.json')


def test_loopback_host_client_origin_and_auth(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get('/health', headers={'host': 'attacker.example'}).status_code == 400
        assert client.get('/health', headers={'origin': 'https://attacker.example'}).status_code == 403
        assert client.get('/status').status_code == 401
        assert client.get('/status', headers={'authorization': 'Bearer test-token'}).status_code == 200
        assert client.get('/').headers['x-frame-options'] == 'DENY'
        for _ in range(29):
            assert client.get('/status').status_code == 401
        assert client.get('/status').status_code == 429
    with TestClient(create_app(settings), client=('192.168.1.50', 50000)) as remote:
        assert remote.get('/health').status_code == 403


def test_request_size_before_json_parser(settings):
    with TestClient(create_app(settings)) as client:
        response = client.post('/chat', content=b'x'*(256*1024+1), headers={'authorization':'Bearer test-token'})
        assert response.status_code == 413


def test_chunked_size_guard(settings):
    reached = []
    async def app(scope, receive, send):
        reached.append(True)
    events = iter([{'type':'http.request', 'body':b'x'*200000, 'more_body':True},
                   {'type':'http.request', 'body':b'x'*100000, 'more_body':False}])
    sent = []
    async def receive():
        return next(events)
    async def send(event):
        sent.append(event)
    scope = {'type':'http','method':'POST','path':'/chat','scheme':'http','client':('127.0.0.1',1),
             'headers':[(b'host',b'127.0.0.1'),(b'authorization',b'Bearer test-token')]}
    asyncio.run(SecurityMiddleware(app, settings)(scope, receive, send))
    assert sent[0]['status'] == 413
    assert not reached


@pytest.mark.parametrize('relative',['../outside','.hidden/a.md','C:\\secret.txt','a.md:secret','credentials.json'])
def test_private_and_windows_paths(tmp_path, relative):
    with pytest.raises(SecurityError):
        safe_path(tmp_path,relative)


def test_links_inside_authorized_root_are_rejected(tmp_path):
    target=tmp_path/'target'; target.mkdir(); (target/'a.md').write_text('private')
    (tmp_path/'alias').symlink_to(target, target_is_directory=True)
    with pytest.raises(SecurityError):
        safe_path(tmp_path,'alias/a.md')
    os.link(target/'a.md',tmp_path/'hard.md')
    with pytest.raises(SecurityError):
        safe_path(tmp_path,'hard.md')


def test_local_mode_removes_external_and_executable_tools(settings):
    local=replace(settings,privacy_mode='local',allow_executables=True,enable_plugins=True)
    registry=create_registry(local,Memory(local.vault))
    assert not {'web_search','consult_models','desktop_run_executable'} & registry.tools.keys()
    with pytest.raises(SecurityError):
        local_endpoint('https://example.com')
    local_endpoint('http://127.0.0.1:11434')
