@echo off
setlocal
pushd "%~dp0"
title Importar dados para o Cronos

set "SOURCE=%~dp0Dados-Para-Importar"
if not exist "%SOURCE%" (
  mkdir "%SOURCE%"
  echo PASTA DE IMPORTACAO CRIADA
  echo.
  echo Copie para Dados-Para-Importar a pasta antiga completa ou os arquivos do vault.
  echo.
  echo Depois execute este arquivo novamente. Ele detectara o formato automaticamente.
  pause
  popd
  exit /b 0
)

if not exist ".venv\Scripts\python.exe" (
  echo Preparando o Cronos para importar os dados...
  call "%~dp0Instalar-Cronos.bat"
  if errorlevel 1 (
    popd
    exit /b 1
  )
)

if exist "%SOURCE%\.env" (
  if exist "%SOURCE%\vault" (
    ".venv\Scripts\python.exe" "%~dp0tools\migrate_local_data.py" --source "%SOURCE%"
  ) else (
    echo A pasta contem .env, mas nao contem vault. Nenhum dado foi alterado.
    set "RESULT=1"
    goto finish
  )
) else (
  ".venv\Scripts\python.exe" "%~dp0tools\import_vault_folder.py" --source "%SOURCE%" --target "%~dp0vault"
)
set "RESULT=%ERRORLEVEL%"
:finish
if "%RESULT%"=="0" (
  echo.
  echo Pronto. O proximo inicio do Cronos usara as memorias importadas.
  echo Execute ABRIR-CRONOS.bat para iniciar.
) else (
  echo.
  echo A importacao nao terminou. Os arquivos de origem foram mantidos.
)
echo.
pause
popd
exit /b %RESULT%
