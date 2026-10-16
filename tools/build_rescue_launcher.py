"""Embed the dependency-free helper into one Windows BAT, with no downloads."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    header = r'''@echo off
setlocal
set "CRONOS_RESCUE_SELF=%~f0"
set "CRONOS_RESCUE_FOLDER=%~dp0"
powershell.exe -NoLogo -NoProfile -Command "$ErrorActionPreference='Stop'; try { Add-Type -AssemblyName System.Windows.Forms; $root=$env:CRONOS_RESCUE_FOLDER; if (-not ((Test-Path -LiteralPath (Join-Path $root '.env')) -or (Test-Path -LiteralPath (Join-Path $root 'cronos')))) { $picker=New-Object System.Windows.Forms.FolderBrowserDialog; $picker.Description='Escolha a pasta ATUAL do Cronos com .env e cronos. Nao escolha um ZIP.'; if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }; $root=$picker.SelectedPath }; $question=[System.Windows.Forms.MessageBox]::Show('Feche o Cronos antes do backup. Continuar com a copia de seguranca da pasta selecionada? Nenhuma atualizacao sera instalada.','Salvar e abrir Cronos',[System.Windows.Forms.MessageBoxButtons]::OKCancel); if ($question -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }; $python=Join-Path $root '.venv\Scripts\python.exe'; $prefix=@(); if (-not (Test-Path -LiteralPath $python)) { if (Get-Command py.exe -ErrorAction SilentlyContinue) { $python='py.exe'; $prefix=@('-3') } elseif (Get-Command python.exe -ErrorAction SilentlyContinue) { $python='python.exe' } else { throw 'Python nao encontrado. O ambiente .venv pode ter sido apagado. Mantenha a pasta com seus dados.' } }; $raw=[IO.File]::ReadAllText($env:CRONOS_RESCUE_SELF); $parts=$raw -split '(?m)^# CRONOS_RESCUE_PYTHON\r?$'; if ($parts.Length -ne 2) { throw 'Arquivo incompleto; baixe novamente o BAT.' }; $temporary=Join-Path ([IO.Path]::GetTempPath()) ('cronos-rescue-'+[Guid]::NewGuid().ToString('N')+'.py'); [IO.File]::WriteAllText($temporary,$parts[1],(New-Object Text.UTF8Encoding($false))); try { & $python @prefix $temporary $root; $result=$LASTEXITCODE } finally { Remove-Item -LiteralPath $temporary -ErrorAction SilentlyContinue }; exit $result } catch { Write-Host ('Nao foi possivel iniciar: '+$_.Exception.Message); exit 1 }"
set "CRONOS_RESCUE_RESULT=%errorlevel%"
echo.
pause
exit /b %CRONOS_RESCUE_RESULT%
# CRONOS_RESCUE_PYTHON
'''
    output = ROOT / 'releases/SALVAR-E-ABRIR-CRONOS.bat'
    output.write_bytes((header + (ROOT / 'tools/rescue_installation.py').read_text()).replace('\n', '\r\n').encode('utf-8'))
    return output


if __name__ == '__main__': print(build())
