"""Build a self-contained, streaming R50 to R56 Windows updater.

The ZIP is appended to the BAT and read there by Python's ZipFile. The user
does not need a second temporary ZIP or a second full Cronos installation.
"""
from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

try:
    from tools.build_complete_bundle import build_patch
except ModuleNotFoundError:
    from build_complete_bundle import build_patch


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'releases/CRONOS-Atualizacao-Preservando-Dados.zip'
OUTPUT = ROOT / 'releases/INSTALADOR-CRONOS-R50-PRESERVANDO-DADOS.bat'
REVISION = 'cronos-interface-referencia-2026-11-15-r56'

HEADER = r"""@echo off
setlocal
set "CRONOS_PATCH_SELF=%~f0"
set "CRONOS_PATCH_TARGET=%USERPROFILE%\Cronos-R50"
if not exist "%CRONOS_PATCH_TARGET%\.venv\Scripts\python.exe" (
  echo Escolha a pasta do Cronos R50 que voce ja usa, com suas integracoes.
  for /f "usebackq delims=" %%I in (`powershell.exe -NoLogo -NoProfile -STA -Command "Add-Type -AssemblyName System.Windows.Forms; $dialog=New-Object System.Windows.Forms.FolderBrowserDialog; $dialog.Description='Escolha a pasta do Cronos R50 instalado'; if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::WriteLine($dialog.SelectedPath) }"`) do set "CRONOS_PATCH_TARGET=%%I"
)
if not exist "%CRONOS_PATCH_TARGET%\.venv\Scripts\python.exe" (
  echo Nao encontrei o Python da instalacao antiga. Escolha a pasta Cronos-R50 instalada.
  pause
  exit /b 1
)
if not exist "%CRONOS_PATCH_TARGET%\.env" (
  echo A pasta escolhida nao contem .env. Nenhum arquivo foi alterado.
  pause
  exit /b 1
)
echo Feche a janela do Cronos antes de atualizar.
"%CRONOS_PATCH_TARGET%\.venv\Scripts\python.exe" -c "import os,zipfile;exec(zipfile.ZipFile(os.environ['CRONOS_PATCH_SELF']).read('tools/apply_embedded_update.py'))"
if errorlevel 1 (
  echo Nao foi possivel atualizar. A instalacao anterior foi preservada.
  pause
  exit /b 1
)
if exist "%CRONOS_PATCH_TARGET%\ABRIR-CRONOS.bat" call "%CRONOS_PATCH_TARGET%\ABRIR-CRONOS.bat"
exit /b %errorlevel%
"""


def build() -> tuple[Path, int]:
    build_patch()
    with ZipFile(ARCHIVE) as package:
        if package.testzip() is not None:
            raise ValueError('The update ZIP failed its integrity check.')
        names = set(package.namelist())
        if not {'tools/apply_embedded_update.py', 'tools/interface_update_manifest.json',
                'cronos/ui/index.html'} <= names:
            raise ValueError('The update ZIP is missing required files.')
        manifest = json.loads(package.read('tools/interface_update_manifest.json'))
        if manifest.get('revision') != REVISION:
            raise ValueError('The update ZIP is not the verified R56 revision.')
        if '.env' in names or 'config/providers.json' in names or any(name.startswith('vault/') for name in names):
            raise ValueError('Private data cannot enter the installer.')
    header = HEADER.replace('\n', '\r\n').encode('ascii')
    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open('wb') as destination, ARCHIVE.open('rb') as source:
        destination.write(header)
        while part := source.read(1024 * 1024):
            destination.write(part)
    if OUTPUT.stat().st_size != len(header) + ARCHIVE.stat().st_size:
        raise ValueError('The self-contained update is incomplete.')
    with ZipFile(OUTPUT) as package:
        if package.testzip() is not None:
            raise ValueError('Python cannot read the embedded ZIP.')
    return OUTPUT, len(header)


if __name__ == '__main__':
    path, offset = build()
    print(json.dumps({'file': str(path), 'size_bytes': path.stat().st_size,
                      'payload_offset': offset}))
