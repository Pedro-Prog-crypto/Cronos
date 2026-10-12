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
".venv\Scripts\python.exe" -m pip install --upgrade "pip>=26.2"
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install -e ".[desktop,search]"
if errorlevel 1 goto :failed
if not exist ".env" copy ".env.example" ".env" >nul
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
