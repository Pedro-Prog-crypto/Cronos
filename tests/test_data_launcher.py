import base64,hashlib,importlib.util,io,json
from pathlib import Path
from types import SimpleNamespace
import zipfile
import pytest
from tools import data_launcher as launcher
from tools import build_data_launcher as builder
from test_local_update import fixture as installation, updater


def test_first_use_updates_existing_root_preserving_private_files_and_records_backup(tmp_path):
    source,root,private=installation(tmp_path)
    manifest=source/'tools/interface_update_manifest.json'
    value=json.loads(manifest.read_text());value['revision']='fixture-version';manifest.write_text(json.dumps(value))
    calls=[]
    def backup(path):
        calls.append(path);folder=tmp_path/'private-backup';folder.mkdir();return folder,{'complete':True}
    launcher.prepare(root,source,updater,backup)
    assert calls==[root] and (root/'cronos/app.py').read_text()=='new=True\n'
    assert all((root/name).read_bytes()==value for name,value in private.items())
    assert json.loads((root/'.cronos-local/data-launcher/installed.json').read_text())['installed_once']
    # Future changes are authoritative; reopening an older BAT cannot roll them back.
    new_note=root/'vault/Temas/nova-memoria.md'
    new_note.write_text('Memoria criada depois da atualizacao.')
    (root/'cronos/app.py').write_text('future_version=True\n')
    assert launcher.prepare(root,source,updater,backup) is None
    assert (root/'cronos/app.py').read_text()=='future_version=True\n' and len(calls)==1
    assert new_note.read_text()=='Memoria criada depois da atualizacao.'


def test_backup_failure_never_applies_code_or_writes_success_marker(tmp_path):
    source,root,private=installation(tmp_path)
    before=(root/'cronos/app.py').read_bytes()
    def fail(_):raise OSError('disk full')
    with pytest.raises(OSError):launcher.prepare(root,source,updater,fail)
    assert (root/'cronos/app.py').read_bytes()==before
    assert not (root/'.cronos-local/data-launcher/installed.json').exists()
    assert all((root/name).read_bytes()==data for name,data in private.items())


def test_new_launcher_ignores_an_old_updater_runner_and_always_uses_selected_root(tmp_path):
    _,root,_=installation(tmp_path)
    old=root/'.cronos-local/updater/runner.py';old.parent.mkdir(parents=True);old.write_text('raise RuntimeError()')
    python=root/'.venv/Scripts/pythonw.exe';python.parent.mkdir(parents=True);python.write_bytes(b'fixture')
    calls=[];launcher.launch(root,popen=lambda *a,**kw:calls.append((a,kw)))
    assert calls[0][0][0]==[str(python),'-m','cronos.supervisor']
    assert calls[0][1]['cwd']==str(root) and 'shell' not in calls[0][1]


def test_missing_dependencies_are_retried_even_after_a_previous_partial_install(tmp_path):
    _,root,_=installation(tmp_path)
    for name in ('python.exe','pythonw.exe'):
        p=root/'.venv/Scripts'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
    (root/'pyproject.toml').write_text('[project]\nname="test"\n')
    calls=[]
    def run(args,**kw):calls.append(args);return SimpleNamespace(returncode=1 if len(calls)==1 else 0)
    launcher.ensure_environment(root,run=run)
    assert len(calls)==3 and calls[1][1:]==['-m','pip','install','-e',str(root)]


def test_one_bat_contains_verified_current_code_without_private_data(tmp_path,monkeypatch):
    output=builder.build()
    text=output.read_text(encoding='utf-8')
    header,embedded=text.split('\n# CRONOS_DATA_PYTHON\n')
    assert max(map(len,header.splitlines()))<8000
    assert 'Invoke-WebRequest' not in header and 'DownloadString' not in header
    namespace={'__name__':'embedded_test'};exec(compile(embedded,'launcher.py','exec'),namespace)
    payload=base64.b64decode(namespace['PAYLOAD_BASE64'])
    assert hashlib.sha256(payload).hexdigest()==namespace['PAYLOAD_SHA256']
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names=set(archive.namelist())
        assert {'cronos/live_screen.py','cronos/studio/engineering.py','cronos/ui/index.html'}<=names
        assert not any(name in names for name in ('.env','config/providers.json'))
        assert not any(name.startswith(('vault/','.venv/')) for name in names)
        assert b'PROCESS_FILES' in archive.read('tools/rescue_installation.py')
    namespace['unpack'](tmp_path/'payload')
    with zipfile.ZipFile(output.with_suffix('.zip')) as archive:
        assert archive.namelist()==[output.name] and archive.read(output.name)==output.read_bytes()


def test_changed_embedded_package_is_rejected_before_extracting(tmp_path):
    with pytest.raises(ValueError,match='alterado'):
        launcher.unpack(tmp_path/'payload',base64.b64encode(b'damaged'),'0'*64)
    assert not (tmp_path/'payload').exists()


def test_real_backup_under_update_lock_never_reads_the_locked_control_file(tmp_path,monkeypatch):
    import sqlite3
    from tools import rescue_installation as rescue
    source,root,private=installation(tmp_path)
    manifest=source/'tools/interface_update_manifest.json'
    manifest.write_text(json.dumps({**json.loads(manifest.read_text()),'revision':'fixed-lock-fixture'}))
    lock=root/'.cronos-local/updater/supervisor.lock'
    copy=rescue.copy_file
    attempts=[]
    def mandatory_windows_lock(origin,destination):
        attempts.append(origin)
        if origin==lock:
            error=PermissionError('The process cannot access the locked byte');error.winerror=33;raise error
        return copy(origin,destination)
    monkeypatch.setattr(rescue,'copy_file',mandatory_windows_lock)
    db=root/'vault/.cronos/memory.sqlite3'
    db.unlink()
    with sqlite3.connect(db) as memory:
        memory.execute('PRAGMA journal_mode=WAL')
        memory.execute('CREATE TABLE notes(text)')
        memory.execute('INSERT INTO notes VALUES(?)',('Memoria salva antes da atualizacao',));memory.commit()
        saved=launcher.prepare(root,source,updater,lambda selected:rescue.snapshot(selected,tmp_path/'backups'))
    assert lock.is_file() and lock not in attempts
    report=json.loads((saved/'RELATORIO.json').read_text())
    assert str(lock) in report['excluded'] and report['complete']
    assert (saved/'instalacao/.env').read_bytes()==private['.env']
    assert (saved/'instalacao/config/providers.json').read_bytes()==private['config/providers.json']
    assert not (saved/'instalacao/.cronos-local/updater/supervisor.lock').exists()
    with sqlite3.connect(saved/'instalacao/vault/.cronos/memory.sqlite3') as backup:
        assert backup.execute('SELECT text FROM notes').fetchone()[0]=='Memoria salva antes da atualizacao'
    assert (root/'cronos/app.py').read_text()=='new=True\n'


def test_locked_user_data_is_not_silently_omitted_or_marked_as_a_success(tmp_path,monkeypatch):
    from tools import rescue_installation as rescue
    source,root,private=installation(tmp_path)
    copy=rescue.copy_file
    def locked_private_file(origin,destination):
        if origin==root/'config/providers.json':
            error=PermissionError('Private file locked');error.winerror=33;raise error
        return copy(origin,destination)
    monkeypatch.setattr(rescue,'copy_file',locked_private_file)
    original=(root/'cronos/app.py').read_bytes()
    with pytest.raises((OSError,ValueError)):
        launcher.prepare(root,source,updater,lambda selected:rescue.snapshot(selected,tmp_path/'backups'))
    assert (root/'cronos/app.py').read_bytes()==original
    assert all((root/name).read_bytes()==data for name,data in private.items())
    assert not (root/'.cronos-local/data-launcher/installed.json').exists()
    assert (next((tmp_path/'backups').iterdir())/'INCOMPLETO.txt').is_file()
