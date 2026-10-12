@echo off
setlocal
pushd "%~dp0"
if exist ".venv\Scripts\python.exe" ".venv\Scripts\python.exe" -m cronos.wake --stop
popd
