"""Retain SQLite handles to expose locks normally hidden by garbage collection on Linux."""
from contextlib import closing
from datetime import date, timedelta
import importlib.util
import io
from pathlib import Path
import sqlite3
import tempfile
from zipfile import ZipFile

from fastapi.testclient import TestClient
import pytest

from cronos.app import create_app
from cronos.studio import runtime, service
from cronos.studio.store import Store
from test_backend import settings, AUTH
from test_studio import Builder, new, generate


@pytest.fixture
def handles(monkeypatch):
    opened=[]
    real_connect=sqlite3.connect
    class TrackedConnection(sqlite3.Connection):
        closed=False
        def close(self):
            super().close()
            self.closed=True
    def tracked(path,*args,**kwargs):
        kwargs['factory']=TrackedConnection
        kwargs['check_same_thread']=False  # Inspect retained test handles from the client thread.
        db=real_connect(path,*args,**kwargs)
        opened.append((Path(path),db))
        return db
    monkeypatch.setattr(sqlite3,'connect',tracked)
    yield opened
    for _,db in opened:db.close()


def assert_closed(opened):
    assert opened
    assert all(db.closed for _,db in opened), 'SQLite handles still open; Windows cannot remove the database.'
    for _,db in opened:
        with pytest.raises(sqlite3.ProgrammingError,match='closed'):
            sqlite3.Connection.execute(db,'SELECT 1')


def test_form_checks_close_all_handles_before_temporary_directory_cleanup(handles,monkeypatch):
    original=tempfile.TemporaryDirectory
    folders=[]
    class WindowsCleanup(original):
        def __enter__(self):
            folder=super().__enter__();folders.append(Path(folder));return folder
        def __exit__(self,*args):
            # Retained handles model Windows sharing rules at the exact cleanup boundary.
            assert_closed([(path,db) for path,db in handles if path.parent==Path(self.name)])
            return super().__exit__(*args)
    monkeypatch.setattr(tempfile,'TemporaryDirectory',WindowsCleanup)
    for _ in range(3):
        results=service.backend_checks()
        assert results and all(check['status']=='passed' for check in results)
    assert len(folders)==3 and all(not folder.exists() for folder in folders)
    assert_closed(handles)


def test_form_submit_closes_after_commit_and_rolls_back_conflicting_slot(handles,tmp_path):
    path=tmp_path/'forms.sqlite3'
    data={'name':'Senhor teste','email':'test@example.com','message':'Contato','consent':True}
    runtime.submit(path,'contact',data)
    booking={**data,'date':str(date.today()+timedelta(days=1)),'time':'12:30','service':'Teste'}
    runtime.submit(path,'booking',booking)
    with pytest.raises(runtime.FormError):runtime.submit(path,'booking',booking)
    assert_closed(handles)
    with closing(sqlite3.connect(path)) as db:
        assert db.execute('SELECT count(*) FROM submissions').fetchone()[0]==2
        assert db.execute('SELECT count(*) FROM slots').fetchone()[0]==1
    assert_closed(handles)


@pytest.mark.parametrize('kind',['runtime','store'])
def test_connections_close_even_if_database_setup_fails(monkeypatch,tmp_path,kind):
    opened=[]
    real_connect=sqlite3.connect
    class BrokenSetup(sqlite3.Connection):
        closed=False
        def execute(self,sql,*args):raise sqlite3.OperationalError('simulated PRAGMA failure')
        def close(self):super().close();self.closed=True
    def tracked(path,*args,**kwargs):
        kwargs['factory']=BrokenSetup;db=real_connect(path,*args,**kwargs);opened.append((Path(path),db));return db
    monkeypatch.setattr(sqlite3,'connect',tracked)
    try:
        with pytest.raises(sqlite3.OperationalError):
            if kind=='runtime':
                with runtime.connect(tmp_path/'broken.sqlite3'):pass
            else:Store(tmp_path/'vault')
        assert_closed(opened)
    finally:
        for _,db in opened:db.close()


def test_project_connections_commit_rollback_and_close_without_gc(handles,tmp_path):
    store=Store(tmp_path/'vault')
    project=store.new({'name':'Projeto preservado','category':'restaurante'})
    files={'index.html':'<h1>Salvo</h1>','styles.css':'','app.js':''}
    store.commit(project,files,'Versão salva',{'passed':True})
    assert store.get(project['id'])['revision']==0
    assert store.revision(project)['files']==files and len(store.history(project))==1
    with pytest.raises(RuntimeError,match='rollback'):
        with store.connect() as db:
            db.execute('DELETE FROM revisions WHERE project=?',(project['id'],))
            raise RuntimeError('rollback')
    assert len(store.history(project))==1
    assert_closed(handles)


def test_preview_submission_list_closes_read_connections(settings,monkeypatch):
    with TestClient(create_app(settings,Builder())) as client:
        project=new(client)
        data={'name':'Teste','email':'test@example.com','message':'Olá','consent':True}
        assert client.post('/studio/projects/'+project['id']+'/forms',headers=AUTH,json={'revision':0,'kind':'contact','data':data}).status_code==200
        real_connect=sqlite3.connect;opened=[]
        class Tracked(sqlite3.Connection):
            closed=False
            def close(self):super().close();self.closed=True
        def tracked(path,*args,**kwargs):
            kwargs['factory']=Tracked;kwargs['check_same_thread']=False;db=real_connect(path,*args,**kwargs)
            if '.cronos/studio' in Path(path).as_posix():opened.append((Path(path),db))
            return db
        with monkeypatch.context() as patch:
            patch.setattr(sqlite3,'connect',tracked)
            result=client.get('/studio/projects/'+project['id']+'/submissions',headers=AUTH)
            assert result.status_code==200 and len(result.json()['submissions'])==1
            assert_closed(opened)


def test_exported_server_also_closes_sqlite_handles(settings,tmp_path,handles):
    with TestClient(create_app(settings,Builder())) as client:
        project=generate(client,new(client))
        package=client.get('/studio/projects/'+project['id']+'/export',headers=AUTH)
        with ZipFile(io.BytesIO(package.content)) as archive:
            target=tmp_path/'server.py';target.write_bytes(archive.read('server.py'))
        spec=importlib.util.spec_from_file_location('exported_studio_lifecycle',target)
        exported=importlib.util.module_from_spec(spec);spec.loader.exec_module(exported)
        exported.submit(tmp_path/'exported.sqlite3','contact',{'name':'Teste','email':'test@example.com','message':'Olá','consent':True})
        assert_closed([(path,db) for path,db in handles if path.name=='exported.sqlite3'])
