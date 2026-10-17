import importlib.util
import json
from pathlib import Path
import sqlite3
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cronos_rescue', ROOT / 'tools/rescue_installation.py')
rescue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rescue)


def installation(tmp_path):
    root = tmp_path / 'Cronos com espacos'
    (root / 'cronos').mkdir(parents=True)
    (root / '.env').write_text('MISTRAL_API_KEY=private-example\nCRONOS_VAULT=vault\n')
    (root / 'cronos/app.py').write_text('version = "Mistral user changes"\n')
    (root / 'vault/Temas').mkdir(parents=True)
    (root / 'vault/Temas/nota.md').write_text('Memoria importante')
    (root / 'config').mkdir()
    (root / 'config/providers.json').write_text('{"providers":["minha-integracao"]}')
    return root


def test_backup_preserves_keys_integrations_code_and_committed_wal(tmp_path):
    root = installation(tmp_path)
    (root / '.venv').mkdir()
    (root / '.venv/python.exe').write_bytes(b'dependency')
    database = root / 'vault/memory.sqlite3'
    with sqlite3.connect(database) as live:
        live.execute('PRAGMA journal_mode=WAL')
        live.execute('CREATE TABLE notes(text)')
        live.execute('INSERT INTO notes VALUES(?)', ('Dado confirmado',))
        live.commit()
        backup, report = rescue.snapshot(root, tmp_path / 'backups')
        with sqlite3.connect(backup / 'instalacao/vault/memory.sqlite3') as saved:
            assert saved.execute('SELECT text FROM notes').fetchone()[0] == 'Dado confirmado'
        assert report['files']['instalacao/vault/memory.sqlite3']['sqlite_snapshot']
    assert (backup / 'instalacao/.env').read_bytes() == (root / '.env').read_bytes()
    assert (backup / 'instalacao/config/providers.json').read_bytes() == (root / 'config/providers.json').read_bytes()
    assert (backup / 'instalacao/cronos/app.py').read_text() == 'version = "Mistral user changes"\n'
    assert (root / 'vault/Temas/nota.md').read_text() == 'Memoria importante'
    assert not (backup / 'instalacao/.venv').exists()
    assert not (backup / 'INCOMPLETO.txt').exists()
    assert json.loads((backup / 'RELATORIO.json').read_text())['complete']


def test_external_vault_personality_and_providers_are_copied_without_import(tmp_path):
    root = installation(tmp_path)
    external = tmp_path / 'Obsidian separado'
    external.mkdir()
    (external / 'nota.md').write_text('Conhecimento externo')
    providers = tmp_path / 'integracoes.json'
    providers.write_text('{"saved":true}')
    (root / '.env').write_text(f'CRONOS_VAULT="{external}" # comentario\nCRONOS_PROVIDERS_FILE="{providers}"\nTOKEN=do-not-log\n')
    backup, report = rescue.snapshot(root, tmp_path / 'backups')
    assert (backup / 'dados-externos/CRONOS_VAULT/nota.md').read_text() == 'Conhecimento externo'
    assert (backup / 'dados-externos/CRONOS_PROVIDERS_FILE').read_text() == '{"saved":true}'
    assert 'do-not-log' not in json.dumps(report)


def test_missing_runtime_does_not_prevent_data_backup(tmp_path):
    root = installation(tmp_path)
    backup, report = rescue.snapshot(root, tmp_path / 'backups')
    assert report['complete'] and (backup / 'instalacao/vault/Temas/nota.md').is_file()
    assert any('.venv' in issue for issue in rescue.diagnose(root))
    (root / 'cronos/broken.py').write_text('def invalid(:\n')
    assert any('broken.py' in issue for issue in rescue.diagnose(root))


def test_failure_marks_incomplete_and_does_not_launch_or_modify_source(tmp_path, monkeypatch):
    root = installation(tmp_path)
    original = (root / '.env').read_bytes()
    def fail(*a): raise OSError('simulated full disk')
    monkeypatch.setattr(rescue, 'copy_file', fail)
    with pytest.raises(OSError): rescue.snapshot(root, tmp_path / 'backups')
    folder = next((tmp_path / 'backups').iterdir())
    assert (folder / 'INCOMPLETO.txt').exists() and not (folder / 'RELATORIO.json').exists()
    assert (root / '.env').read_bytes() == original


def test_nested_backups_and_links_are_rejected(tmp_path):
    root = installation(tmp_path)
    with pytest.raises(ValueError): rescue.snapshot(root, root / 'backup')
    (root / 'atalho').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError): rescue.snapshot(root, tmp_path / 'backups')


def test_launcher_runs_selected_code_without_stale_updater_or_shell(tmp_path):
    root = installation(tmp_path)
    stale = root / '.cronos-local/updater/runner.py'
    stale.parent.mkdir(parents=True)
    stale.write_text('raise RuntimeError("old updater")')
    calls = []
    rescue.launch(root, tmp_path / 'startup.log', popen=lambda *a, **kw:calls.append((a, kw)))
    args, options = calls[0]
    assert args[0] == [str(root / '.venv/Scripts/pythonw.exe'), '-m', 'cronos.supervisor']
    assert options['cwd'] == str(root) and 'shell' not in options


def test_bat_embeds_the_verified_helper_and_has_no_network(tmp_path):
    spec = importlib.util.spec_from_file_location('rescue_builder', ROOT / 'tools/build_rescue_launcher.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    (tmp_path/'tools').mkdir()
    (tmp_path/'releases').mkdir()
    (tmp_path/'tools/rescue_installation.py').write_bytes((ROOT/'tools/rescue_installation.py').read_bytes())
    builder.ROOT=tmp_path
    destination = builder.build()
    raw = destination.read_text(encoding='utf-8')
    embedded = raw.split('\n# CRONOS_RESCUE_PYTHON\n')[1]
    assert embedded == (ROOT / 'tools/rescue_installation.py').read_text()
    compile(embedded, 'embedded-rescue.py', 'exec')
    with zipfile.ZipFile(destination.with_suffix('.zip')) as archive:
        assert archive.namelist() == [destination.name]
        assert archive.read(destination.name) == destination.read_bytes()
    header = raw.split('\n# CRONOS_RESCUE_PYTHON\n')[0]
    assert len(header.splitlines()[4]) < 8000
    assert not any(term in header.lower() for term in ('https://', 'invoke-webrequest', 'downloadstring', ' pip '))


def test_sqlite_snapshot_closes_both_handles_before_reporting_success(tmp_path,monkeypatch):
    source=tmp_path/'notes.sqlite3';destination=tmp_path/'copy.sqlite3'
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE notes(text)');db.execute('INSERT INTO notes VALUES(?)',('Memoria nova',))
    db.close()
    connections=[];connect=sqlite3.connect
    def tracked(*args,**kwargs):
        connection=connect(*args,**kwargs);connections.append(connection);return connection
    monkeypatch.setattr(rescue.sqlite3,'connect',tracked)
    result=rescue.copy_file(source,destination)
    assert result['sqlite_snapshot'] and len(connections)==2
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError,match='closed'):connection.execute('SELECT 1')


def test_a_user_file_with_the_same_lock_name_is_still_backed_up(tmp_path):
    root=installation(tmp_path)
    note=root/'vault/Temas/supervisor.lock';note.write_text('Arquivo do usuario, nao um mutex do iniciador.')
    backup,report=rescue.snapshot(root,tmp_path/'backups')
    assert (backup/'instalacao/vault/Temas/supervisor.lock').read_text()==note.read_text()
    assert report['complete'] and str(note) not in report['excluded']
