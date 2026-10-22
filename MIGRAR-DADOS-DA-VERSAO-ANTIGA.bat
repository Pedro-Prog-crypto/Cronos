@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Preparando o Cronos para migrar seus dados nesta pasta...
  call "%~dp0Instalar-Cronos.bat"
  if errorlevel 1 (
    popd
    exit /b 1
  )
)
".venv\Scripts\python.exe" "%~dp0tools\migrate_local_data.py"
set "RESULT=%ERRORLEVEL%"
echo.
pause
popd
exit /b %RESULT%
