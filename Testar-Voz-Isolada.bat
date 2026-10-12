@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Execute Instalar-Cronos.bat primeiro.
    pause
    popd
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m cronos.voice_diagnostic
popd
