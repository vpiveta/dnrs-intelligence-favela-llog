@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Publicar DNR's Intelligence Favela Llog
color 0E

echo ======================================================
echo   PUBLICACAO - DNR's Intelligence Favela Llog
echo ======================================================
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Git nao encontrado.
  echo Abrindo a pagina oficial do Git for Windows...
  start "" "https://git-scm.com/download/win"
  echo Instale o Git, reinicie o computador e execute este BAT novamente.
  pause
  exit /b 1
)

if exist "instance\flip.db" (
  echo [OK] Banco local encontrado e protegido pelo .gitignore.
)
if exist ".env" (
  echo [ATENCAO] O arquivo .env nao sera enviado ao GitHub.
)

if not exist ".git" (
  git init
  git branch -M main
)

git remote get-url origin >nul 2>&1
if errorlevel 1 (
  git remote add origin https://github.com/vpiveta/flip-enterprise.git
) else (
  git remote set-url origin https://github.com/vpiveta/flip-enterprise.git
)

echo.
echo Arquivos que NAO serao enviados: banco, uploads, backups, logs, .env e ambiente virtual.
echo.
set /p MSG=Mensagem da atualizacao [DNR Intelligence - atualizacao]: 
if "%MSG%"=="" set MSG=DNR Intelligence - atualizacao

git add .
git status --short
git commit -m "%MSG%"
if errorlevel 1 echo Nenhuma alteracao nova para registrar ou commit ja existente.

echo.
echo Enviando para o GitHub...
git push -u origin main
if errorlevel 1 (
  echo.
  echo [ERRO] Nao foi possivel enviar.
  echo Verifique o login do GitHub, a internet e a permissao no repositorio.
  echo O navegador pode abrir para autorizar sua conta.
  pause
  exit /b 1
)

echo.
echo [OK] Codigo publicado no GitHub.
echo Abrindo o repositorio...
start "" "https://github.com/vpiveta/flip-enterprise"
echo.
echo PROXIMO PASSO:
echo 1. Crie o banco no Supabase.
echo 2. Copie a URL do Session Pooler.
echo 3. Crie um Web Service no Render conectado ao GitHub.
echo 4. Informe DATABASE_URL no Render.
echo.
set /p ABRIR=Deseja abrir Supabase e Render agora? [S/N]: 
if /I "%ABRIR%"=="S" (
  start "" "https://supabase.com/dashboard"
  start "" "https://dashboard.render.com/"
)
pause
