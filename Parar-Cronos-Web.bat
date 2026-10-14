@echo off
setlocal
pushd "%~dp0"
if exist ".cronos-local\updater" echo stop> ".cronos-local\updater\stop.request"
popd
