@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Execute Instalar-Cronos.bat primeiro.
    popd
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m cronos.desktop
if errorlevel 1 (
    echo Nao foi possivel abrir o Cronos. Confira o erro acima.
    echo Para erros do renderizador, instale o Microsoft Edge WebView2 Runtime.
    pause
)
popd
