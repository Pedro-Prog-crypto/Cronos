@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Execute Instalar-Cronos.bat primeiro.
    popd
    pause
    exit /b 1
)
if exist ".cronos-local\updater\runner.py" (
    start "" ".venv\Scripts\pythonw.exe" ".cronos-local\updater\runner.py" --run "%CD%"
) else (
    start "" ".venv\Scripts\pythonw.exe" -m cronos.supervisor
)
popd
