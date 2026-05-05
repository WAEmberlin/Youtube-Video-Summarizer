@echo off
setlocal
cd /d "%~dp0"
python -m pip install -q -r requirements.txt
python gui.py
if errorlevel 1 pause
exit /b %ERRORLEVEL%
