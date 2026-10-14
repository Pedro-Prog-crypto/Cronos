@echo off
setlocal
pushd "%~dp0"
if not exist "pyproject.toml" (
    echo Extraia todos os arquivos do projeto antes de instalar.
    goto :failed
)
if not exist ".venv\Scripts\python.exe" (
    py -m venv .venv
    if errorlevel 1 goto :failed
)
".venv\Scripts\python.exe" -c "import struct,sys;sys.exit(0 if sys.version_info >= (3,11) and struct.calcsize('P') == 8 else 1)"
if errorlevel 1 (
    echo Instale Python 3.11 ou 3.12 de 64 bits e recrie o ambiente virtual.
    goto :failed
)
".venv\Scripts\python.exe" -m pip install --upgrade "pip>=26.2"
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install -e ".[desktop,search,wake]"
if errorlevel 1 goto :failed
echo Preparando suporte de reproducao de musica e clipes...
".venv\Scripts\python.exe" -m cronos.media_runtime
if errorlevel 1 goto :failed
if not exist ".env" copy ".env.example" ".env" >nul
".venv\Scripts\python.exe" -m cronos.recognition --prepare
if errorlevel 1 echo Modelo portugues pendente. Execute esta instalacao novamente com internet.
echo Instalacao concluida. Configure suas chaves no arquivo .env.
echo Depois abra Iniciar-Cronos.bat.
notepad ".env"
popd
pause
exit /b 0
:failed
echo Nao foi possivel instalar. Confira o erro acima e se Python 3.11+ esta instalado.
popd
pause
exit /b 1
