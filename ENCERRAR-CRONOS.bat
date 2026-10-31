@echo off
setlocal
pushd "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" -c "from cronos.wake import stop; from cronos.resident import stop_active; from cronos.background_listener import hide_window; stop(); stop_active(); hide_window()"
)
popd
exit /b 0
