"""The low-space BAT updates an installed R50 without copying private data."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from tools import apply_embedded_update, build_low_space_installer


def fixture(tmp_path):
    target = tmp_path / 'Cronos-R50'
    (target / 'cronos/ui').mkdir(parents=True)
    (target / 'config').mkdir()
    (target / 'vault').mkdir()
    private = {
        '.env': b'PRIVATE_TEST_KEY=unchanged\n',
        'config/providers.json': b'{"private":"unchanged"}',
        'vault/memory.txt': b'private memory',
    }
    for name, content in private.items():
        (target / name).write_bytes(content)
    code = {'cronos/app.py': b'old_app=True\n', 'cronos/ui/index.html': b'<html>new interface</html>'}
    (target / 'cronos/app.py').write_bytes(code['cronos/app.py'])
    (target / 'cronos/ui/index.html').write_bytes(b'<html>old interface</html>')
    manifest = {'revision': apply_embedded_update.REVISION,
                'files': {name: hashlib.sha256(content).hexdigest() for name, content in code.items()}}
    archive = tmp_path / 'instalador.bat'
    with archive.open('wb') as output:
        output.write(b'@echo off\r\nexit /b 0\r\n')
    with ZipFile(archive, 'a') as package:
        package.writestr('tools/interface_update_manifest.json', json.dumps(manifest))
        for name, content in code.items():
            package.writestr(name, content)
    return archive, target, private


def test_updates_only_changed_code_and_preserves_integrations(tmp_path):
    archive, target, private = fixture(tmp_path)
    backup, changed = apply_embedded_update.apply(archive, target)
    assert changed == 1
    assert (target / 'cronos/ui/index.html').read_bytes() == b'<html>new interface</html>'
    assert (backup / 'cronos/ui/index.html').read_bytes() == b'<html>old interface</html>'
    assert not (backup / 'cronos/app.py').exists()
    assert all((target / name).read_bytes() == content for name, content in private.items())
    assert apply_embedded_update.apply(archive, target) == (None, 0)


def test_failed_update_restores_code_and_private_files(tmp_path, monkeypatch):
    archive, target, private = fixture(tmp_path)
    replace = apply_embedded_update.os.replace

    def fail_on_manifest(source, destination):
        if str(destination).endswith('tools/interface_update_manifest.json'):
            raise OSError('simulated disk failure')
        return replace(source, destination)

    monkeypatch.setattr(apply_embedded_update.os, 'replace', fail_on_manifest)
    with pytest.raises(OSError, match='simulated disk failure'):
        apply_embedded_update.apply(archive, target)
    assert (target / 'cronos/ui/index.html').read_bytes() == b'<html>old interface</html>'
    assert all((target / name).read_bytes() == content for name, content in private.items())


def test_low_disk_space_is_reported_before_changing_code(tmp_path, monkeypatch):
    archive, target, private = fixture(tmp_path)
    monkeypatch.setattr(apply_embedded_update.shutil, 'disk_usage', lambda _path: SimpleNamespace(free=0))
    with pytest.raises(ValueError, match='Espaco insuficiente'):
        apply_embedded_update.apply(archive, target)
    assert (target / 'cronos/ui/index.html').read_bytes() == b'<html>old interface</html>'
    assert all((target / name).read_bytes() == content for name, content in private.items())


def test_downloadable_bat_contains_verified_update_zip():
    output, offset = build_low_space_installer.build()
    assert output.read_bytes()[:offset].startswith(b'@echo off\r\n')
    assert output.stat().st_size == offset + build_low_space_installer.ARCHIVE.stat().st_size
    assert output.stat().st_size < 60 * 1024 * 1024
    with ZipFile(output) as package:
        assert package.testzip() is None
        assert 'tools/apply_embedded_update.py' in package.namelist()
        assert '.env' not in package.namelist()
