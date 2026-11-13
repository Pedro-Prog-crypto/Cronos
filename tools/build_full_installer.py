"""Wrap the complete, code-only Cronos ZIP in one self-extracting Windows BAT.

This installer creates a fresh folder. It never reads or publishes .env, vault,
provider keys, or data from an older Cronos installation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'releases/CRONOS-Completo-Um-Arquivo.zip'
OUTPUT = ROOT / 'releases/INSTALAR-CRONOS-COMPLETO-R46.bat'
INSTALL_FOLDER = 'Cronos-R46'
OFFSET_MARKER = '0000000000'

# No data migration or replacement is performed. A complete existing release folder
# is opened as-is, so running an older download cannot overwrite newer work.
POWERSHELL = r"""$ErrorActionPreference='Stop';
$target=Join-Path $env:USERPROFILE '__INSTALL_FOLDER__';
if (Test-Path -LiteralPath $target) {
  $manifest=Join-Path $target 'tools\interface_update_manifest.json';
  if (-not (Test-Path -LiteralPath (Join-Path $target 'cronos\app.py')) -or -not (Test-Path -LiteralPath (Join-Path $target 'ABRIR-CRONOS.bat')) -or -not (Test-Path -LiteralPath $manifest)) { throw 'A pasta __INSTALL_FOLDER__ ja existe, mas esta incompleta. Renomeie-a antes de instalar uma copia nova.' };
  $version=(Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json).revision;
  if ($version -ne '__REVISION__') { throw 'A pasta __INSTALL_FOLDER__ ja contem outra versao. Ela nao foi substituida.' };
  Write-Host ('Abrindo o Cronos existente em '+$target);
  exit 0;
};
$archive=Join-Path ([IO.Path]::GetTempPath()) ('cronos-completo-'+[Guid]::NewGuid().ToString('N')+'.zip');
$stage=$target+'-instalando-'+[Guid]::NewGuid().ToString('N').Substring(0,8);
try {
  $reader=[IO.File]::OpenRead($env:CRONOS_FULL_SELF);
  try {
    [void]$reader.Seek(__OFFSET__,[IO.SeekOrigin]::Begin);
    $writer=[IO.File]::Create($archive);
    try { $reader.CopyTo($writer) } finally { $writer.Dispose() };
  } finally { $reader.Dispose() };
  if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne '__SHA256__') { throw 'O download esta incompleto ou alterado. Baixe novamente; nada foi instalado.' };
  Add-Type -AssemblyName System.IO.Compression.FileSystem;
  [IO.Compression.ZipFile]::ExtractToDirectory($archive,$stage);
  $manifest=Join-Path $stage 'tools\interface_update_manifest.json';
  if (-not (Test-Path -LiteralPath (Join-Path $stage 'cronos\app.py')) -or -not (Test-Path -LiteralPath (Join-Path $stage 'ABRIR-CRONOS.bat')) -or -not (Test-Path -LiteralPath (Join-Path $stage 'pyproject.toml')) -or -not (Test-Path -LiteralPath $manifest)) { throw 'O pacote completo nao passou na verificacao de arquivos.' };
  if ((Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json).revision -ne '__REVISION__') { throw 'A versao extraida nao corresponde ao instalador.' };
  Move-Item -LiteralPath $stage -Destination $target;
  Write-Host ('Cronos completo instalado em '+$target);
} finally {
  Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue;
  if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue };
}"""

HEADER = r"""@echo off
setlocal
set "CRONOS_FULL_SELF=%~f0"
powershell.exe -NoLogo -NoProfile -Command "__SCRIPT__"
if errorlevel 1 (
  echo Nao foi possivel instalar o Cronos completo. Nenhuma pasta antiga foi alterada.
  pause
  exit /b 1
)
if not exist "%USERPROFILE%\__INSTALL_FOLDER__\.env" (
  echo Importando memorias e integracoes da versao antiga, sem envia-las ao GitHub.
  py -3 "%USERPROFILE%\__INSTALL_FOLDER__\tools\restore_existing_data.py" --target "%USERPROFILE%\__INSTALL_FOLDER__"
  if errorlevel 1 (
    echo O programa completo foi instalado, mas os dados antigos nao foram importados.
    echo Execute este mesmo arquivo novamente para escolher a pasta antiga.
    pause
    exit /b 1
  )
)
if not exist "%USERPROFILE%\__INSTALL_FOLDER__\.venv\Scripts\python.exe" (
  echo Preparando o Python do Cronos nesta pasta. Aguarde a instalacao das dependencias.
  call "%USERPROFILE%\__INSTALL_FOLDER__\Instalar-Cronos.bat"
  if errorlevel 1 exit /b 1
)
call "%USERPROFILE%\__INSTALL_FOLDER__\ABRIR-CRONOS.bat"
exit /b %errorlevel%
"""


def make_header(offset: int, checksum: str, revision: str) -> bytes:
    script = ' '.join(line.strip() for line in POWERSHELL.splitlines())
    script = script.replace('__OFFSET__', f'{offset:010d}')
    script = script.replace('__SHA256__', checksum).replace('__REVISION__', revision).replace('__INSTALL_FOLDER__', INSTALL_FOLDER)
    if any(char in script for char in '"\r\n'):
        raise ValueError('PowerShell header contains an unsafe batch delimiter.')
    return HEADER.replace('__SCRIPT__', script).replace('__INSTALL_FOLDER__', INSTALL_FOLDER).replace('\n', '\r\n').encode('ascii')


def build() -> tuple[Path, int]:
    with zipfile.ZipFile(ARCHIVE) as package:
        if package.testzip():
            raise ValueError('The complete archive failed its CRC check.')
        names = set(package.namelist())
        required = {'ABRIR-CRONOS.bat', 'Instalar-Cronos.bat', 'pyproject.toml',
                    '.env.example', 'cronos/app.py', 'cronos/ui/index.html',
                    'tools/interface_update_manifest.json'}
        if not required <= names:
            raise ValueError('The full application is missing from the archive.')
        if any(name == '.env' or name == 'config/providers.json' or name.startswith(('vault/', '.venv/', '.cronos-local/')) for name in names):
            raise ValueError('Private installation data cannot enter the GitHub installer.')
        revision = json.loads(package.read('tools/interface_update_manifest.json'))['revision']
    if not re.fullmatch(r'[a-z0-9-]+-2026-11-13-r46', revision):
        raise ValueError('The full archive is not the verified R46 release.')
    checksum = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    preliminary = make_header(0, checksum, revision)
    header = make_header(len(preliminary), checksum, revision)
    if len(header) != len(preliminary):
        raise AssertionError('Fixed-width offset changed the header length.')
    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open('wb') as target, ARCHIVE.open('rb') as source:
        target.write(header)
        while part := source.read(1024 * 1024):
            target.write(part)
    if OUTPUT.stat().st_size != len(header) + ARCHIVE.stat().st_size:
        raise ValueError('Incomplete self-extracting installer.')
    return OUTPUT, len(header)


if __name__ == '__main__':
    path, offset = build()
    print(json.dumps({'file': str(path), 'size_bytes': path.stat().st_size, 'payload_offset': offset}))
