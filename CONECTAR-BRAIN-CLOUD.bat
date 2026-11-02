@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Prepare o Cronos pelo ABRIR-CRONOS.bat antes de conectar o Brain Cloud.
  pause
  popd
  exit /b 1
)
".venv\Scripts\python.exe" -m tools.connect_brain_cloud
if errorlevel 1 (
  echo A conexao nao foi salva. Confira se o Brain Cloud esta aberto e se o arquivo foi exportado pela tela Integracao.
)
pause
popd
