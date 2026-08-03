@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Migrar banco para Supabase - DNR Intelligence
color 0B

echo ==========================================================
echo  DNR's Intelligence Favela Llog - Migracao para Supabase
echo ==========================================================
echo.
if not exist "instance\flip.db" (
  echo ERRO: O arquivo instance\flip.db nao foi encontrado.
  echo Copie o banco preenchido para a pasta instance antes de continuar.
  pause
  exit /b 1
)

where py >nul 2>nul
if errorlevel 1 (
  echo ERRO: Python nao encontrado.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente virtual...
  py -3 -m venv .venv
  if errorlevel 1 goto erro
)

call ".venv\Scripts\activate.bat"
echo Instalando/verificando dependencias...
python -m pip install -r requirements-server.txt
if errorlevel 1 goto erro

echo.
echo O proximo passo pedira a DATABASE_URL do Supabase.
echo Nada sera salvo em arquivo.
echo.
python scripts\migrate_sqlite_to_postgres.py "instance\flip.db" --replace
if errorlevel 1 goto erro

echo.
echo Banco migrado. Reinicie o servico no Render se necessario.
pause
exit /b 0

:erro
echo.
echo A operacao terminou com erro. Leia a mensagem acima.
pause
exit /b 1
