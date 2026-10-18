"""Ship a fixed code-only update + data-preserving launcher as one Windows BAT."""
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile
from tools.apply_interface_update import entries

ROOT=Path(__file__).resolve().parents[1]


def build():
    files=entries(ROOT)
    payload=io.BytesIO()
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as package:
        for name in dict.fromkeys([*files,'cronos/persistent_data.py','cronos/supervisor.py','cronos/update_transaction.py','tools/interface_update_manifest.json','tools/apply_interface_update.py','tools/rescue_installation.py']):
            package.write(ROOT/name,name)
    raw=payload.getvalue();encoded=base64.b64encode(raw).decode('ascii')
    encoded='\n'.join(encoded[i:i+120] for i in range(0,len(encoded),120))
    helper=(ROOT/'tools/data_launcher.py').read_text().replace('__PAYLOAD_SHA256__',hashlib.sha256(raw).hexdigest()).replace('__PAYLOAD_BASE64__',encoded)
    header=r'''@echo off
setlocal
set "CRONOS_DATA_SELF=%~f0"
set "CRONOS_DATA_FOLDER=%~dp0"
powershell.exe -NoLogo -NoProfile -Command "$ErrorActionPreference='Stop'; try { Add-Type -AssemblyName System.Windows.Forms; $root=$env:CRONOS_DATA_FOLDER; if (-not (Test-Path -LiteralPath (Join-Path $root 'cronos\app.py'))) { $last=Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Cronos-Dados\.launcher\active-installation.json'; if (Test-Path -LiteralPath $last) { $candidate=(Get-Content -LiteralPath $last -Raw | ConvertFrom-Json).root; if ($candidate -and (Test-Path -LiteralPath (Join-Path $candidate 'cronos\app.py'))) { $root=$candidate } } }; if (-not (Test-Path -LiteralPath (Join-Path $root 'cronos\app.py'))) { $picker=New-Object System.Windows.Forms.FolderBrowserDialog; $picker.Description='Primeira abertura: escolha a pasta extraida do Cronos com seus dados atuais. Nao escolha ZIP ou RAR.'; if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }; $root=$picker.SelectedPath }; $python=Join-Path $root '.venv\Scripts\python.exe'; $prefix=@(); if (-not (Test-Path -LiteralPath $python)) { if (Get-Command py.exe -ErrorAction SilentlyContinue) { $python='py.exe'; $prefix=@('-3') } elseif (Get-Command python.exe -ErrorAction SilentlyContinue) { $python='python.exe' } else { throw 'Python nao encontrado. Instale o Python 3.11 ou mais recente; mantenha a pasta com seus dados.' } }; $raw=[IO.File]::ReadAllText($env:CRONOS_DATA_SELF); $parts=$raw -split '(?m)^# CRONOS_DATA_PYTHON\r?$'; if ($parts.Length -ne 2) { throw 'Arquivo incompleto; baixe novamente.' }; $temporary=Join-Path ([IO.Path]::GetTempPath()) ('cronos-dados-'+[Guid]::NewGuid().ToString('N')+'.py'); [IO.File]::WriteAllText($temporary,$parts[1],(New-Object Text.UTF8Encoding($false))); try { & $python @prefix $temporary $root; $result=$LASTEXITCODE } finally { Remove-Item -LiteralPath $temporary -ErrorAction SilentlyContinue }; exit $result } catch { Write-Host ('Nao foi possivel iniciar: '+$_.Exception.Message); exit 1 }"
set "CRONOS_DATA_RESULT=%errorlevel%"
if not "%CRONOS_DATA_RESULT%"=="0" pause
exit /b %CRONOS_DATA_RESULT%
# CRONOS_DATA_PYTHON
'''
    output=ROOT/'releases/ABRIR-CRONOS-COM-MEUS-DADOS.bat'
    output.write_bytes((header+helper).replace('\n','\r\n').encode('utf-8'))
    with zipfile.ZipFile(output.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as package:
        package.write(output,output.name)
        package.write(ROOT/'docs/DADOS_PERMANENTES.md','LEIA-PRIMEIRO-DADOS.txt')
    return output


if __name__=='__main__':print(build())
