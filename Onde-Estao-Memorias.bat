@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Execute Instalar-Cronos.bat primeiro.
    popd
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m cronos.memory_location
set "CRONOS_LOCATION_RESULT=%errorlevel%"
popd
pause
exit /b %CRONOS_LOCATION_RESULT%
