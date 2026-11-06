"""The direct GitHub BAT contains the whole application, not an update patch."""
import hashlib
import re
import zipfile

from tools import build_full_installer


def test_direct_installer_embeds_complete_verified_archive():
    output, offset = build_full_installer.build()
    header = output.read_bytes()[:offset]
    assert header.startswith(b'@echo off\r\n')
    assert len(header) == offset
    assert b'CRONOS_FULL_SELF=%~f0' in header
    assert b'ABRIR-CRONOS.bat' in header
    assert b'restore_existing_data.py' in header
    assert b'Cronos-R42' in header
    assert header.index(b'restore_existing_data.py') < header.index(b'Instalar-Cronos.bat')
    assert b'Nenhuma pasta antiga foi alterada' in header
    assert b'if (Test-Path -LiteralPath $target)' in header
    assert re.search(rb'Seek\(' + f'{offset:010d}'.encode() + rb',', header)
    payload = output.read_bytes()[offset:]
    original = build_full_installer.ARCHIVE.read_bytes()
    assert payload == original
    assert hashlib.sha256(payload).hexdigest().encode() in header
    with zipfile.ZipFile(output) as package:
        names = set(package.namelist())
        assert package.testzip() is None
        assert {'cronos/app.py', 'cronos/ui/index.html', 'ABRIR-CRONOS.bat',
                'Instalar-Cronos.bat', '.env.example', 'pyproject.toml'} <= names
        assert '.env' not in names and 'config/providers.json' not in names
        assert not any(name.startswith(('vault/', '.venv/')) for name in names)
