"""Real import/reopen/recovery tests, with isolated fake credentials only."""
from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import shutil
import subprocess
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from cronos import persistent_data as data
from cronos import update_transaction as tx
from tools import data_launcher
from tools import rescue_installation
from test_local_update import fixture


def setup(tmp_path, monkeypatch):
    _, root, _ = fixture(tmp_path)
    db = root / 'vault/.cronos/memory.sqlite3'
    db.unlink()
    with closing(sqlite3.connect(db)) as connection:
        connection.execute('CREATE TABLE notes(text)')
        connection.execute('INSERT INTO notes VALUES(?)', ('memoria inicial',))
        connection.commit()
    (root / '.env').write_text('GEMINI_API_KEY="fixture-do-not-log"\nCUSTOM_SETTING=preserved\n')
    (root / 'config/ai_council.json').write_text('{"members":["mistral"]}')
    (root / '.cronos-local/usage.json').write_text('{"count":7}')
    monkeypatch.setattr(Path, 'home', lambda: tmp_path / 'user')
    return root, tmp_path / 'Documents/Cronos-Dados'


def test_imports_all_data_from_consistent_backup_without_changing_originals(tmp_path, monkeypatch, capsys):
    root, home = setup(tmp_path, monkeypatch)
    original = (root / '.env').read_bytes()
    with closing(sqlite3.connect(root / 'vault/.cronos/memory.sqlite3')) as connection:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('INSERT INTO notes VALUES(?)', ('committed in WAL',)); connection.commit()
        selected, backup = data.import_data(root, home, rescue_installation)
    assert selected == home and backup.is_dir()
    assert (root / '.env').read_bytes() == original
    assert (home / 'config/ai_council.json').read_bytes() == (root / 'config/ai_council.json').read_bytes()
    assert (home / 'config/providers.json').read_bytes() == (root / 'config/providers.json').read_bytes()
    assert (home / 'vault/.cronos/studio/projects.sqlite3').read_bytes() == (root / 'vault/.cronos/studio/projects.sqlite3').read_bytes()
    assert (home / '.cronos-local/usage.json').is_file()
    assert (home / 'modelos/personalidades/cronos.md').read_text() == 'personalidade personalizada'
    with closing(sqlite3.connect(home / 'vault/.cronos/memory.sqlite3')) as connection:
        assert connection.execute('SELECT text FROM notes').fetchall() == [('memoria inicial',), ('committed in WAL',)]
    assert 'fixture-do-not-log' not in capsys.readouterr().out
    assert 'fixture-do-not-log' not in (home / data.MARKER).read_text()
    assert 'fixture-do-not-log' not in (root / data.POINTER).read_text()
    assert not (home / '.cronos-local/updater').exists()


def test_two_code_versions_share_new_keys_integrations_and_memories_without_old_import(tmp_path, monkeypatch):
    for key in ('CRONOS_DATA_HOME', 'CRONOS_VAULT', 'CRONOS_PERSONALITY', 'CRONOS_PROVIDERS_FILE', 'GEMINI_API_KEY', 'NEW_API_KEY', 'CUSTOM_SETTING'):
        monkeypatch.setenv(key, os.getenv(key, ''))
    root, home = setup(tmp_path, monkeypatch)
    data.import_data(root, home, rescue_installation)
    (home / '.env').write_text((home / '.env').read_text() + '\nNEW_API_KEY=fixture-new\n')
    (home / 'config/providers.json').write_text('{"providers":["new-integration"]}')
    with closing(sqlite3.connect(home / 'vault/.cronos/memory.sqlite3')) as connection:
        connection.execute('INSERT INTO notes VALUES(?)', ('memoria nova',)); connection.commit()
    older = tmp_path / 'old-code'; older.mkdir()
    # No .env or vault is needed in a second code installation once imported.
    selected, backup = data.import_data(older, home, SimpleNamespace(snapshot=lambda _: pytest.fail('Reimported old data')))
    assert selected == home and backup is None
    monkeypatch.chdir(root)
    data.activate(root); load_dotenv('.env', override=True)
    from cronos.config import Settings
    first = Settings.from_env()
    monkeypatch.chdir(older)
    data.activate(older); load_dotenv('.env', override=True)
    second = Settings.from_env()
    assert first.vault == second.vault == home / 'vault'
    assert first.providers_file == second.providers_file == home / 'config/providers.json'
    assert os.getenv('NEW_API_KEY') == 'fixture-new'
    assert second.providers_file.read_text() == '{"providers":["new-integration"]}'
    with closing(sqlite3.connect(second.vault / '.cronos/memory.sqlite3')) as connection:
        assert ('memoria nova',) in connection.execute('SELECT text FROM notes').fetchall()
    # Don't leak fake env values or permanent-data settings into other tests.
    for key in ('CRONOS_DATA_HOME', 'CRONOS_VAULT', 'CRONOS_PERSONALITY', 'CRONOS_PROVIDERS_FILE', 'GEMINI_API_KEY', 'NEW_API_KEY', 'CUSTOM_SETTING'):
        monkeypatch.delenv(key, raising=False)


def test_external_custom_vault_personality_and_provider_paths_are_imported(tmp_path, monkeypatch):
    root, home = setup(tmp_path, monkeypatch)
    external = tmp_path / 'external'; external.mkdir()
    (external / 'notes').mkdir(); (external / 'notes/new.md').write_text('cofre externo real')
    (external / 'profile.md').write_text('personalidade externa')
    (external / 'integrations.json').write_text('{"external":true}')
    with (root / '.env').open('a') as output:
        for key, path in {'CRONOS_VAULT': external/'notes', 'CRONOS_PROVIDERS_FILE': external/'integrations.json',
                          'CRONOS_PERSONALITY': external/'profile.md'}.items():
            output.write(key + '=' + json.dumps(str(path)) + '\n')
    data.import_data(root, home, rescue_installation)
    assert (home / 'vault/new.md').read_text() == 'cofre externo real'
    assert not (home / 'vault/Temas/math.md').exists()
    assert (home / 'config/providers.json').read_text() == '{"external":true}'
    assert (home / 'modelos/personalidades/cronos.md').read_text() == 'personalidade externa'


def test_failed_import_never_publishes_or_edits_source_and_retry_works(tmp_path, monkeypatch):
    root, home = setup(tmp_path, monkeypatch)
    original = (root / '.env').read_bytes()
    copy = data.shutil.copytree
    def fail(*args, **kwargs): raise OSError('fixture disk full')
    monkeypatch.setattr(data.shutil, 'copytree', fail)
    with pytest.raises(OSError, match='disk full'): data.import_data(root, home, rescue_installation)
    assert not home.exists() and not (root / data.POINTER).exists()
    assert (root / '.env').read_bytes() == original
    assert list(home.parent.glob('Cronos-Dados-importando-*/IMPORTACAO-INCOMPLETA.txt'))
    monkeypatch.setattr(data.shutil, 'copytree', copy)
    assert data.import_data(root, home, rescue_installation)[0] == home


def test_existing_unrecognized_data_and_missing_configured_vault_are_never_overwritten(tmp_path, monkeypatch):
    root, home = setup(tmp_path, monkeypatch)
    home.mkdir(parents=True); (home / '.env').write_text('unknown-private-data')
    with pytest.raises(ValueError, match='sem registro'): data.import_data(root, home, rescue_installation)
    assert (home / '.env').read_text() == 'unknown-private-data'
    with (root / '.env').open('a') as out: out.write('\nCRONOS_VAULT=missing-vault\n')
    with pytest.raises(ValueError, match='cofre'): data.import_data(root, tmp_path/'other-data', rescue_installation)
    assert not (tmp_path/'other-data').exists()


def test_code_rollback_does_not_restore_old_shared_memory(tmp_path, monkeypatch):
    root, home = setup(tmp_path, monkeypatch)
    data.import_data(root, home, rescue_installation)
    transaction = tmp_path/'transaction'; transaction.mkdir()
    tx.write_json(transaction/'memory-backup.json', {'vault': str(home/'vault'), 'name': 'missing-old-archive.zip'})
    # The old archive isn't even read. New data remains authoritative.
    tx.restore_memory(transaction)
    assert (home/'vault/Temas/math.md').read_text() == 'Notas do usuario'


def test_shared_folder_lock_refuses_simultaneous_sessions(tmp_path):
    path = tmp_path/'session.lock'
    with data.locked(path):
        script = 'from cronos.persistent_data import locked; import sys\nwith locked(sys.argv[1]): pass'
        result = subprocess.run([sys.executable, '-c', script, str(path)], capture_output=True)
        assert result.returncode != 0 and b'BlockingIOError' in result.stderr
    with data.locked(path): pass


def test_launcher_starts_external_supervisor_with_shared_data_environment(tmp_path):
    root = tmp_path/'code'; executable = root/'.venv/Scripts/pythonw.exe'
    executable.parent.mkdir(parents=True); executable.write_bytes(b'fixture')
    home = tmp_path/'Cronos-Dados'; runner = home/'.launcher/version/runner.py'
    calls = []
    data_launcher.launch(root, home=home, runner=runner, popen=lambda *a, **kw: calls.append((a,kw)))
    args, options = calls[0]
    assert args[0] == [str(executable), str(runner), '--run', str(root)]
    assert options['env']['CRONOS_DATA_HOME'] == str(home)
    assert options['cwd'] == str(root) and 'shell' not in options


def test_real_memory_continues_after_changing_code_installations(tmp_path, monkeypatch):
    from cronos.storage import Memory
    root, home = setup(tmp_path, monkeypatch)
    (root/'vault/.cronos/memory.sqlite3').unlink()
    original = Memory(root/'vault'); session = uuid4()
    original.record(session, 'Qual e a capital do Brasil?', 'Brasilia.', [])
    data.import_data(root, home, rescue_installation)
    current = Memory(home/'vault')
    current.record(session, 'E do Amazonas?', 'Manaus.', [])
    previous_version = tmp_path/'previous-version'; previous_version.mkdir()
    data.import_data(previous_version, home, SimpleNamespace(snapshot=lambda _: pytest.fail('Old data imported')))
    reopened = Memory(data.selected_home(previous_version)/'vault')
    assert [turn['content'] for turn in reopened.history(session)] == [
        'Qual e a capital do Brasil?', 'Brasilia.', 'E do Amazonas?', 'Manaus.']
    assert len(original.history(session)) == 2


def test_standalone_supervisor_runs_old_browser_against_permanent_env_and_memory(tmp_path, monkeypatch):
    root, home = setup(tmp_path, monkeypatch)
    data.import_data(root, home, rescue_installation)
    # Simulate an older installation without the new persistent-data module.
    old = tmp_path/'older-code'; (old/'cronos').mkdir(parents=True)
    (old/'cronos/__init__.py').write_text('')
    (old/'.env').write_text('GEMINI_API_KEY=wrong-old-fixture\n')
    source = Path(__file__).resolve().parents[1]/'cronos'
    shutil.copy2(source/'config.py', old/'cronos/config.py')
    (old/'cronos/browser.py').write_text('''
import json
from pathlib import Path
from dotenv import load_dotenv
from cronos.config import Settings
import sqlite3
load_dotenv('.env', override=True)
settings=Settings.from_env()
with sqlite3.connect(settings.vault/'.cronos/memory.sqlite3') as db:
    db.execute('INSERT INTO notes VALUES(?)', ('saved by older code',))
Path('functional-result.json').write_text(json.dumps({
    'cwd':str(Path.cwd()),'vault':str(settings.vault),
    'providers':str(settings.providers_file),'correct_key':settings.gemini_key=='fixture-do-not-log'}))
''')
    driver = home/'.launcher/test-driver'; driver.mkdir(parents=True)
    for name in ('supervisor.py', 'update_transaction.py', 'persistent_data.py'):
        shutil.copy2(source/name, driver/('runner.py' if name=='supervisor.py' else name))
    environment = {**os.environ, 'CRONOS_DATA_HOME':str(home)}
    result = subprocess.run([sys.executable, str(driver/'runner.py'), '--run', str(old)],
                            env=environment, cwd=old, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr.decode()
    report = json.loads((home/'functional-result.json').read_text())
    assert report == {'cwd':str(home),'vault':str(home/'vault'),
                      'providers':str(home/'config/providers.json'),'correct_key':True}
    assert not (old/'functional-result.json').exists()
    with closing(sqlite3.connect(home/'vault/.cronos/memory.sqlite3')) as db:
        assert ('saved by older code',) in db.execute('SELECT text FROM notes').fetchall()


def test_downloaded_bat_imports_once_then_opens_new_version_without_replacing_data(tmp_path, monkeypatch):
    root, home = setup(tmp_path, monkeypatch)
    package = Path(__file__).resolve().parents[1]/'releases/ABRIR-CRONOS-COM-MEUS-DADOS.bat'
    embedded = package.read_text().split('\n# CRONOS_DATA_PYTHON\n')[1]
    namespace = {'__name__':'embedded_integration'}
    exec(compile(embedded, 'downloaded-launcher.py', 'exec'), namespace)
    original_load = namespace['load']
    def load(name, path):
        module = original_load(name,path)
        if name == 'data_launcher_persistent': module.default_home = lambda: home
        return module
    namespace['load'] = load
    namespace['ensure_environment'] = lambda _: None  # No Windows interpreter here.
    calls = []
    namespace['launch'] = lambda *args, **kwargs: calls.append((args,kwargs))
    monkeypatch.setattr(sys, 'argv', ['downloaded-launcher.py',str(root)])
    assert namespace['main']() == 0
    assert (home/'config/providers.json').read_bytes() == (root/'config/providers.json').read_bytes()
    assert data.selected_home(root) == home
    assert calls[-1][1]['home'] == home
    driver = calls[-1][1]['runner']
    assert driver.is_file() and (driver.parent/'persistent_data.py').is_file()
    assert (driver.parent/'update_transaction.py').is_file()
    (home/'vault/Temas/new-after-import.md').write_text('Memoria posterior')
    # An extracted new version without private keys/cofre must use existing data.
    next_version = tmp_path/'next-version'; (next_version/'cronos').mkdir(parents=True)
    (next_version/'cronos/app.py').write_text('placeholder=True\n')
    monkeypatch.setattr(sys, 'argv', ['downloaded-launcher.py',str(next_version)])
    assert namespace['main']() == 0
    assert data.selected_home(next_version) == home
    assert calls[-1][0] == (next_version,)
    assert (home/'vault/Temas/new-after-import.md').read_text() == 'Memoria posterior'
    assert 'fixture-do-not-log' not in (next_version/'.env').read_text()
    assert not (next_version/'vault').exists()
    # Reopening the older BAT never overlays later code or shared data.
    (next_version/'cronos/app.py').write_text('future_code=True\n')
    assert namespace['main']() == 0
    assert (next_version/'cronos/app.py').read_text() == 'future_code=True\n'
