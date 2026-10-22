@echo off
setlocal
pushd "%~dp0"
if not exist "pyproject.toml" (
  echo Extraia o pacote completo do Cronos antes de instalar.
  goto :failed
)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :failed
)
".venv\Scripts\python.exe" -c "import struct,sys;sys.exit(0 if sys.version_info >= (3,11) and struct.calcsize('P') == 8 else 1)"
if errorlevel 1 (
  echo O Cronos precisa do Python 3.11 ou superior, de 64 bits.
  goto :failed
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install -e ".[desktop,search,wake]"
if errorlevel 1 goto :failed
echo Preparando o suporte local de audio...
".venv\Scripts\python.exe" -m cronos.media_runtime
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m cronos.recognition --prepare
if errorlevel 1 echo Modelo de transcricao pendente; o restante da instalacao terminou.
echo Instalacao concluida nesta pasta.
popd
exit /b 0
:failed
echo Instalacao incompleta. Confira Python 3.11+ de 64 bits e acesso a internet.
popd
pause
exit /b 1
