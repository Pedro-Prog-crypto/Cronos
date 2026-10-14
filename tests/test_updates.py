import asyncio
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import zipfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from cronos import update_transaction as tx
from cronos.updates import UpdateService
from cronos.config import Settings
from cronos.app import create_app


FAKE_BROWSER='''import os,json
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
VERSION="old"
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  data=json.dumps({'ready':True,'version':VERSION}).encode()
  self.send_response(200);self.end_headers();self.wfile.write(data)
port=int(os.environ['CRONOS_MANAGED_PORT'])
Path('port.txt').write_text(str(port))
HTTPServer(('127.0.0.1',port),Handler).serve_forever()
'''


def installation(tmp_path):
    root=tmp_path/'app';(root/'cronos/ui/assets').mkdir(parents=True)
    (root/'pyproject.toml').write_text('[project]\nname="test"\n')
    (root/'.env').write_text('MY_PRIVATE_KEY=secret-before')
    (root/'cronos/__init__.py').write_text('')
    for name in ('app.py','engine.py','config.py'):(root/'cronos'/name).write_text('value="old"\n')
    (root/'cronos/browser.py').write_text(FAKE_BROWSER)
    (root/'cronos/ui/index.html').write_text('<script src="./assets/test.js"></script>')
    (root/'cronos/ui/assets/test.js').write_text('old')
    return root


def package(root, changes=None, extra=None):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        archive.writestr('release/pyproject.toml',(root/'pyproject.toml').read_bytes())
        for name in tx.managed_files(root):
            archive.writestr('release/cronos/'+name,(changes or {}).get(name,(root/'cronos'/name).read_bytes()))
        for name,value in (extra or {}).items():archive.writestr(name,value)
    return output.getvalue()


def prepared(root, data=None):
    transaction=root/'.cronos-local/updater/transactions'/('a'*32)
    transaction.mkdir(parents=True)
    archive=transaction/'release.zip';archive.write_bytes(data or package(root,{'engine.py':b'value="new"\n'}))
    candidate=tx.prepare_archive(archive,transaction/'candidate',root)
    tx.write_json(transaction/'prepared.json',{'revision':'b'*40,'candidate':candidate,'baseline':tx.managed_files(root)})
    return transaction


def test_transaction_backup_install_restore_preserves_private_data(tmp_path):
    root=installation(tmp_path);before=tx.managed_files(root)
    transaction=prepared(root)
    tx.snapshot_private(root,transaction)
    tx.apply(root,transaction)
    assert (root/'cronos/engine.py').read_text()=='value="new"\n'
    assert tx.inventory(transaction/'backup/cronos')==before
    (root/'.env').write_text('broken migration')
    assert tx.restore(root,transaction)
    tx.restore_private(root,transaction)
    assert tx.managed_files(root)==before
    assert (root/'.env').read_text()=='MY_PRIVATE_KEY=secret-before'


@pytest.mark.parametrize('name',['release/../.env','release/cronos/../../.env','release/cronos/CON.py','release/cronos/a:stream','release/cronos/dir\\evil.py'])
def test_malicious_archive_paths_rejected(tmp_path,name):
    root=installation(tmp_path)
    archive=tmp_path/'bad.zip';archive.write_bytes(package(root,extra={name:'bad'}))
    with pytest.raises(ValueError):tx.prepare_archive(archive,tmp_path/'stage',root)
    assert (root/'.env').read_text()=='MY_PRIVATE_KEY=secret-before'


def test_syntax_dependency_and_tampering_checks(tmp_path):
    root=installation(tmp_path)
    archive=tmp_path/'bad.zip';archive.write_bytes(package(root,{'engine.py':b'def invalid('}))
    with pytest.raises(SyntaxError):tx.prepare_archive(archive,tmp_path/'stage',root)
    transaction=prepared(root)
    (transaction/'candidate/cronos/engine.py').write_text('modified after review')
    with pytest.raises(ValueError,match='mudou'):tx.apply(root,transaction)
    assert not (transaction/'backup').exists()


def test_local_change_since_preparation_refuses_install(tmp_path):
    root=installation(tmp_path);transaction=prepared(root)
    (root/'cronos/engine.py').write_text('user modification')
    with pytest.raises(ValueError,match='instalação mudou'):tx.apply(root,transaction)
    assert (root/'cronos/engine.py').read_text()=='user modification'


def test_dependency_changes_require_installer(tmp_path):
    root=installation(tmp_path);archive=tmp_path/'bad.zip'
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as z:z.writestr('release/pyproject.toml','different')
    archive.write_bytes(output.getvalue())
    with pytest.raises(ValueError,match='dependências'):tx.prepare_archive(archive,tmp_path/'stage',root)


def test_partial_file_failure_has_a_recoverable_journal(tmp_path,monkeypatch):
    root=installation(tmp_path);transaction=prepared(root);before=tx.managed_files(root)
    replace=os.replace;count=0
    def fail(source,destination):
        nonlocal count
        if str(destination).startswith(str(root/'cronos')):
            count+=1
            if count==2:raise OSError('simulated power loss')
        return replace(source,destination)
    monkeypatch.setattr(os,'replace',fail)
    with pytest.raises(OSError):tx.apply(root,transaction)
    monkeypatch.setattr(os,'replace',replace)
    assert tx.restore(root,transaction)
    assert tx.managed_files(root)==before


@pytest.mark.parametrize('broken',[False,True])
def test_independent_supervisor_installs_or_restores_after_startup_failure(tmp_path,broken):
    root=installation(tmp_path)
    changes={'browser.py':b'raise RuntimeError("candidate failed")\n'} if broken else {'browser.py':FAKE_BROWSER.replace('VERSION="old"','VERSION="new"').encode()}
    transaction=prepared(root,package(root,changes))
    runner=Path(__file__).resolve().parents[1]/'cronos/supervisor.py'
    # This standalone runner resolves its sibling stdlib transaction engine, not candidate imports.
    process=subprocess.Popen([sys.executable,str(runner),'--run',str(root)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    folder=root/'.cronos-local/updater'
    try:
        deadline=time.monotonic()+10
        while not (root/'port.txt').exists() and time.monotonic()<deadline:time.sleep(.05)
        assert (root/'port.txt').exists()
        tx.write_json(folder/'install.request.json',{'id':'a'*32})
        expected='restored' if broken else 'completed'
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            state=tx.read_json(folder/'status.json',{})
            if state.get('phase')==expected:break
            assert process.poll() is None
            time.sleep(.1)
        assert state['phase']==expected,state
        port=int((root/'port.txt').read_text())
        deadline=time.monotonic()+5
        while True:
            try:
                with httpx.Client(trust_env=False) as client:response=client.get(f'http://127.0.0.1:{port}/updates/health')
                break
            except httpx.ConnectError:
                assert time.monotonic()<deadline;time.sleep(.05)
        assert response.json()['version']==('old' if broken else 'new')
        assert (root/'.env').read_text()=='MY_PRIVATE_KEY=secret-before'
    finally:
        (folder/'stop.request').write_text('stop')
        try:process.communicate(timeout=12)
        except subprocess.TimeoutExpired:process.kill();process.communicate()


def test_same_origin_cookie_restores_browser_session_only_when_managed(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path);monkeypatch.setenv('CRONOS_SUPERVISED','1')
    settings=replace(Settings.from_env(),token='test-local-session',vault=tmp_path/'vault')
    with TestClient(create_app(settings)) as client:
        assert client.get('/connection',headers={'Sec-Fetch-Site':'same-origin'}).status_code==401
        assert client.get('/status',headers={'Authorization':'Bearer '+settings.token}).status_code==200
        assert client.get('/connection',headers={'Sec-Fetch-Site':'cross-site'}).status_code==401
        assert client.get('/connection',headers={'Origin':'https://evil.example','Sec-Fetch-Site':'same-origin'}).status_code==403
        assert client.get('/connection',headers={'Sec-Fetch-Site':'same-origin'}).json()['token']==settings.token
        assert 'HttpOnly' in client.get('/status',headers={'Authorization':'Bearer '+settings.token}).headers['set-cookie']


def test_async_preparation_downloads_only_pinned_official_source(tmp_path,monkeypatch):
    root=installation(tmp_path);data=package(root)
    app=SimpleNamespace(state=SimpleNamespace(engine=SimpleNamespace(settings=SimpleNamespace(privacy_mode='online'))))
    service=UpdateService(app,root)
    original=httpx.AsyncClient
    requests=[]
    def handler(request):requests.append(request);return httpx.Response(200,content=data)
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler)))
    async def run():
        result=await service.prepare('a'*40)
        await service.task
        assert result['installed'] is False
    asyncio.run(run())
    assert service.report()['state']['phase']=='ready'
    assert str(requests[0].url)=='https://codeload.github.com/Pedro-Prog-crypto/Cronos/zip/'+'a'*40
    assert (root/'cronos/engine.py').read_text()=='value="old"\n'


@pytest.mark.parametrize('invalid',[False,True])
def test_requested_code_generation_stages_only_allowed_modules(tmp_path,monkeypatch,invalid):
    from cronos import code_proposals
    from cronos.reply_stream import intro_sink
    root=installation(tmp_path)
    settings=replace(Settings.from_env(),token='not-sent',gemini_key='private-key-not-sent')
    app=SimpleNamespace(state=SimpleNamespace(engine=SimpleNamespace(settings=settings)))
    service=UpdateService(app,root)
    captured=[]
    class Model:
        async def reply(self,system,messages):
            assert intro_sink.get() is None
            captured.append(messages)
            return {'reply':json.dumps({'summary':'Melhora solicitada','changes':[{'path':'cronos/security.py' if invalid else 'cronos/engine.py','content':'value="generated"\n'}],'test_plan':'Verificar comportamento após autorização'}),'topics':[],'tool_calls':[]}
    monkeypatch.setattr(code_proposals,'make_provider',lambda s:Model())
    async def run():
        token=intro_sink.set(lambda text:None)
        try:
            result=await code_proposals.propose(service,'Melhorar o comportamento solicitado',['cronos/engine.py'])
            await service.task
            assert intro_sink.get() is not None
            return result
        finally:intro_sink.reset(token)
    result=asyncio.run(run())
    assert service.report()['state']['phase']==('failed' if invalid else 'ready')
    assert (root/'cronos/engine.py').read_text()=='value="old"\n'
    assert 'private-key-not-sent' not in json.dumps(captured)
    assert 'MY_PRIVATE_KEY' not in json.dumps(captured)
    if not invalid:
        metadata=tx.read_json(service.folder/'transactions'/result['id']/'prepared.json')
        assert metadata['origin']=='ai' and metadata['functional_tests_run'] is False


def test_source_reader_protects_private_paths_and_voice_modules(tmp_path):
    from cronos import code_proposals
    root=installation(tmp_path)
    service=UpdateService(SimpleNamespace(),root)
    for path in ['.env','cronos/../.env','cronos/security.py','cronos/gemini_live.py','cronos/update_transaction.py']:
        with pytest.raises(ValueError):code_proposals.source_file(service,path)
    (root/'cronos/engine.py').write_text('FISH_API_KEY="embedded-secret"')
    with pytest.raises(ValueError,match='credencial'):code_proposals.source_file(service,'cronos/engine.py')


def test_memory_backup_restoration_uses_consistent_sqlite_snapshot(tmp_path):
    import sqlite3
    root=installation(tmp_path);transaction=root/'transaction';transaction.mkdir()
    vault=root/'vault';backups=vault/'.cronos/backups';backups.mkdir(parents=True)
    (vault/'Temas').mkdir();(vault/'Temas/note.md').write_text('original')
    db=vault/'.cronos/memory.sqlite3'
    with sqlite3.connect(db) as connection:connection.execute('CREATE TABLE original(value)')
    name='memory-20261014-120000-12345678.zip'
    with zipfile.ZipFile(backups/name,'w') as archive:
        archive.write(db,'.cronos/memory.sqlite3');archive.write(vault/'Temas/note.md','Temas/note.md')
    tx.write_json(transaction/'memory-backup.json',{'vault':str(vault),'name':name})
    (vault/'Temas/note.md').write_text('broken migration')
    with sqlite3.connect(db) as connection:connection.execute('DROP TABLE original')
    tx.restore_memory(transaction)
    assert (vault/'Temas/note.md').read_text()=='original'
    with sqlite3.connect(db) as connection:assert connection.execute("SELECT name FROM sqlite_master WHERE name='original'").fetchone()


def test_model_discovery_announces_only_observed_changes_without_generation(tmp_path,monkeypatch):
    root=installation(tmp_path)
    settings=replace(Settings.from_env(),gemini_key='configured',providers_file=root/'providers.json')
    app=SimpleNamespace(state=SimpleNamespace(engine=SimpleNamespace(settings=settings)))
    service=UpdateService(app,root)
    calls=[]
    async def listing(settings,ident):calls.append(ident);return ['old-model']
    monkeypatch.setattr('cronos.integrations.available_models',listing)
    asyncio.run(service.discover_models())
    assert not tx.read_json(service.folder/'model-catalogs.json')['advice']
    cache=tx.read_json(service.folder/'model-catalogs.json');cache['checked_at']=0
    tx.write_json(service.folder/'model-catalogs.json',cache)
    async def new_listing(settings,ident):calls.append(ident);return ['old-model','new-model']
    monkeypatch.setattr('cronos.integrations.available_models',new_listing)
    asyncio.run(service.discover_models())
    advice=tx.read_json(service.folder/'model-catalogs.json')['advice']
    assert 'new-model' in advice[0]['title'] and advice[0]['status']=='proposed'
    asyncio.run(service.discover_models())
    assert calls==['gemini','gemini']


def test_prepare_return_creates_another_reviewable_transaction(tmp_path):
    root=installation(tmp_path);transaction=prepared(root);old=tx.managed_files(root)
    tx.apply(root,transaction)
    journal=tx.read_json(transaction/'journal.json');tx.write_json(transaction/'journal.json',{**journal,'phase':'completed'})
    service=UpdateService(SimpleNamespace(),root)
    result=asyncio.run(service.prepare_rollback('a'*32))
    assert not result['installed'] and service.report()['state']['phase']=='ready'
    staged=service.folder/'transactions'/result['id']
    assert tx.inventory(staged/'candidate/cronos')==old
    assert (root/'cronos/engine.py').read_text()=='value="new"\n'


@pytest.mark.parametrize('broken',[False,True])
def test_real_cronos_server_restarts_or_rolls_back_under_independent_supervisor(tmp_path,broken):
    import shutil
    root=installation(tmp_path);source=Path(__file__).resolve().parents[1]/'cronos'
    for module in source.glob('*.py'):shutil.copy2(module,root/'cronos'/module.name)
    shutil.copytree(source/'static',root/'cronos/static')
    (root/'personality.md').write_text('Personalidade de teste, sem geração externa.')
    (root/'.env').write_text('CRONOS_VAULT=vault\nCRONOS_PERSONALITY=personality.md\nGEMINI_API_KEY=\nFISH_API_KEY=\n')
    (root/'cronos/revision.txt').write_text('a'*40)
    browser=root/'cronos/browser.py'
    browser.write_text(browser.read_text().replace("if __name__ == '__main__':", "Path('port.txt').write_text(os.environ.get('CRONOS_MANAGED_PORT','0'))\nif __name__ == '__main__':"))
    changes={'engine.py':b'raise RuntimeError("intentional startup failure")\n'} if broken else {'engine.py':(root/'cronos/engine.py').read_bytes()+b'\n# verified update fixture\n','revision.txt':b'b'*40}
    transaction=prepared(root,package(root,changes))
    before=tx.managed_files(root)
    environment={key:value for key,value in os.environ.items() if key in {'PATH','SYSTEMROOT','WINDIR','TEMP','TMP'}}
    environment.update({'BROWSER':'true','LOCALAPPDATA':str(tmp_path/'local'),'PYTHONDONTWRITEBYTECODE':'1'})
    runner=source/'supervisor.py'
    process=subprocess.Popen([sys.executable,str(runner),'--run',str(root)],env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    folder=root/'.cronos-local/updater'
    try:
        deadline=time.monotonic()+15
        while not (root/'port.txt').exists() and time.monotonic()<deadline:time.sleep(.05)
        assert (root/'port.txt').exists()
        port=int((root/'port.txt').read_text())
        with httpx.Client(trust_env=False) as client:
            while True:
                try:
                    assert client.get(f'http://127.0.0.1:{port}/health').status_code==200;break
                except httpx.ConnectError:
                    assert time.monotonic()<deadline;time.sleep(.1)
            tx.write_json(folder/'install.request.json',{'id':'a'*32})
            expected='restored' if broken else 'completed';deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                state=tx.read_json(folder/'status.json',{})
                if state.get('phase')==expected:break
                assert process.poll() is None
                time.sleep(.1)
            assert state.get('phase')==expected,state
            assert client.get(f'http://127.0.0.1:{port}/health').status_code==200
            if broken:assert tx.managed_files(root)==before
            else:assert (root/'cronos/engine.py').read_bytes().endswith(b'# verified update fixture\n')
            assert 'GEMINI_API_KEY=\n' in (root/'.env').read_text()
    finally:
        (folder/'stop.request').write_text('stop')
        try:process.communicate(timeout=12)
        except subprocess.TimeoutExpired:process.kill();process.communicate()


def test_private_repository_download_never_forwards_key_to_redirect(tmp_path,monkeypatch):
    from cronos.updates import archive_url
    monkeypatch.setenv('CRONOS_UPDATE_GITHUB_TOKEN','private-test-only')
    requests=[]
    def handler(request):
        requests.append(request)
        if request.url.host=='codeload.github.com':return httpx.Response(200,content=b'fixture-zip')
        return httpx.Response(302,headers={'location':'https://codeload.github.com/Pedro-Prog-crypto/Cronos/legacy.zip/'+'a'*40+'?token=temporary'})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            url=await archive_url(client,'a'*40)
            assert url.startswith('https://codeload.github.com/')
            assert requests[0].headers['authorization']=='Bearer private-test-only'
            await client.get(url)
            assert 'authorization' not in requests[1].headers
    asyncio.run(run())
    def evil(request):return httpx.Response(302,headers={'location':'https://evil.example/private.zip'})
    async def refused():
        async with httpx.AsyncClient(transport=httpx.MockTransport(evil)) as client:
            with pytest.raises(ValueError):await archive_url(client,'a'*40)
    asyncio.run(refused())


def test_ai_install_requires_matching_review_before_backup(tmp_path,monkeypatch):
    root=installation(tmp_path);transaction=prepared(root)
    metadata=tx.read_json(transaction/'prepared.json');metadata['origin']='ai';tx.write_json(transaction/'prepared.json',metadata)
    calls=[]
    def backup():calls.append(1);return {'name':'memory-20261014-120000-12345678.zip'}
    app=SimpleNamespace(state=SimpleNamespace(engine=SimpleNamespace(updating=False),panels=SimpleNamespace(backup=backup),memory=SimpleNamespace(vault=root/'vault')))
    service=UpdateService(app,root)
    tx.write_json(service.folder/'status.json',{'phase':'ready','id':'a'*32})
    monkeypatch.setenv('CRONOS_SUPERVISED','1')
    monkeypatch.setenv('CRONOS_SUPERVISOR_PID',str(os.getpid()))
    tx.write_json(service.folder/'heartbeat.json',{'pid':os.getpid(),'at':time.time()})
    with pytest.raises(ValueError,match='Revisar'):asyncio.run(service.install('a'*32))
    assert not calls and not (service.folder/'install.request.json').exists()
    fingerprint=hashlib.sha256(json.dumps(metadata['candidate'],sort_keys=True).encode()).hexdigest()
    tx.write_json(transaction/'reviewed.json',{'fingerprint':fingerprint,'at':time.time()})
    result=asyncio.run(service.install('a'*32))
    assert result['queued'] and calls==[1]
    assert app.state.engine.updating


def test_corrupt_download_becomes_failed_not_a_stuck_preparation(tmp_path,monkeypatch):
    root=installation(tmp_path)
    app=SimpleNamespace(state=SimpleNamespace(engine=SimpleNamespace(settings=SimpleNamespace(privacy_mode='online'))))
    service=UpdateService(app,root)
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(lambda request:httpx.Response(200,content=b'not-a-zip'))))
    async def run():
        await service.prepare('a'*40);await service.task
    asyncio.run(run())
    assert service.report()['state']['phase']=='failed'
    assert (root/'cronos/engine.py').read_text()=='value="old"\n'
