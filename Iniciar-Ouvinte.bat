@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Execute Instalar-Cronos.bat primeiro.
    goto :end
)
echo Ouvinte local: apenas "abrir Cronos". O audio nao e enviado a nuvem.
echo Prepare o modelo pelo modulo Dispositivos e deixe esta janela aberta.
echo Ctrl+C encerra e libera o microfone.
".venv\Scripts\python.exe" -m cronos.wake
:end
popd
pause
