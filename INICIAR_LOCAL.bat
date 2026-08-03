@echo off
setlocal
cd /d "%~dp0"
title DNR's Intelligence Favela Llog

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :erro
)
call .venv\Scripts\activate.bat
python -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :erro
set HOST=127.0.0.1
set PORT=5075
start "" "http://127.0.0.1:5075"
python run.py
exit /b 0
:erro
echo.
echo Nao foi possivel iniciar o sistema.
echo Consulte logs e confirme se o Python esta instalado.
pause
exit /b 1
