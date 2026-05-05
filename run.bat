@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
set EX=%ERRORLEVEL%
if not %EX%==0 echo Exit code: %EX%
pause
exit /b %EX%
