@echo off
setlocal
chcp 65001 >nul
echo Selecione a pasta do Cronos que voce JA USA, com suas APIs e memorias.
echo Nao escolha esta pasta nova que acabou de baixar.
set "CRONOS_UPDATE_TARGET="
for /f "usebackq delims=" %%I in (`powershell.exe -NoProfile -STA -Command "Add-Type -AssemblyName System.Windows.Forms; $dialog = New-Object System.Windows.Forms.FolderBrowserDialog; $dialog.Description = 'Escolha a pasta do Cronos atual, que contem o .env e Iniciar-Cronos-Web.bat'; if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::WriteLine($dialog.SelectedPath) }"`) do set "CRONOS_UPDATE_TARGET=%%I"
if not defined CRONOS_UPDATE_TARGET exit /b 0
if not exist "%CRONOS_UPDATE_TARGET%\.venv\Scripts\python.exe" (
    echo Nao foi encontrado o Python da instalacao atual. Selecione a pasta usada para abrir o Cronos.
    pause
    exit /b 1
)
"%CRONOS_UPDATE_TARGET%\.venv\Scripts\python.exe" -c "import pypdf" >nul 2>&1
if errorlevel 1 (
    echo Preparando o leitor local de PDFs para a area de estudos...
    "%CRONOS_UPDATE_TARGET%\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check "pypdf==6.10.0"
    if errorlevel 1 (
        echo Nao foi possivel instalar o leitor de PDFs. Nenhum arquivo do Cronos foi atualizado.
        pause
        exit /b 1
    )
)
"%CRONOS_UPDATE_TARGET%\.venv\Scripts\python.exe" "%~dp0tools\apply_interface_update.py" "%CRONOS_UPDATE_TARGET%"
set "CRONOS_UPDATE_EXIT=%ERRORLEVEL%"
if "%CRONOS_UPDATE_EXIT%"=="0" if exist "%~dp0Criar-Atalho-Cronos.vbs" cscript.exe //nologo "%~dp0Criar-Atalho-Cronos.vbs" "%CRONOS_UPDATE_TARGET%"
pause
exit /b %CRONOS_UPDATE_EXIT%
