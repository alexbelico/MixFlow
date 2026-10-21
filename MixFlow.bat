@echo off
REM Lanza MixFlow sin consola negra via VBS (pyw/pythonw).
cd /d "%~dp0"
wscript.exe //nologo "%~dp0MixFlow.vbs"
exit /b 0
