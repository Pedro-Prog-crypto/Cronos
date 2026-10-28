@echo off
setlocal
pushd "%~dp0"
set "CRONOS_DATA_HOME="
set "CRONOS_VAULT=%~dp0vault"
set "CRONOS_PROVIDERS_FILE=%~dp0config\providers.json"
set "CRONOS_PERSONALITY=%~dp0modelos\personalidades\cronos.md"
if not exist ".env" copy ".env.example" ".env" >nul
if not exist ".venv\Scripts\pythonw.exe" (
  echo Preparando o Cronos nesta pasta. Isso so precisa ser feito uma vez.
  call "%~dp0Instalar-Cronos.bat"
  if errorlevel 1 (
    popd
    exit /b 1
  )
)
if not exist ".venv\Scripts\pythonw.exe" (
  echo O ambiente local nao foi instalado. Execute Instalar-Cronos.bat.
  pause
  popd
  exit /b 1
)
".venv\Scripts\python.exe" -c "import webview, sounddevice, vosk"
if errorlevel 1 (
  echo Completando os componentes da instalacao...
  call "%~dp0Instalar-Cronos.bat"
  if errorlevel 1 (
    popd
    exit /b 1
  )
)
start "" ".venv\Scripts\pythonw.exe" -m cronos.desktop
popd
exit /b 0
