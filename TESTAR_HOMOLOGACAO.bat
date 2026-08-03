@echo off
setlocal
cd /d "%~dp0"
title Teste de Homologacao - DNR Intelligence
if not exist .venv\Scripts\python.exe (
  py -m venv .venv 2>nul || python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if errorlevel 1 goto erro
python scripts\validate_release.py
if errorlevel 1 goto erro
echo.
echo TESTES CONCLUIDOS COM SUCESSO.
echo Agora execute INICIAR_DNR_INTELLIGENCE.bat e valide com uma planilha de teste.
pause
exit /b 0
:erro
echo.
echo A homologacao encontrou um erro. Copie a mensagem acima.
pause
exit /b 1
