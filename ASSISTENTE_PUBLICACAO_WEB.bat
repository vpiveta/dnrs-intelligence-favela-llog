@echo off
setlocal
cd /d "%~dp0"
title Assistente de Publicacao Web
color 0B
:menu
cls
echo ======================================================
echo  DNR's Intelligence Favela Llog - Assistente Web
echo ======================================================
echo.
echo 1 - Publicar/atualizar codigo no GitHub
echo 2 - Abrir Supabase para criar o banco PostgreSQL
echo 3 - Abrir Render para publicar o sistema
echo 4 - Abrir manual passo a passo
echo 5 - Migrar banco local para PostgreSQL
echo 6 - Sair
echo.
set /p OP=Escolha: 
if "%OP%"=="1" call "%~dp0PUBLICAR_SISTEMA.bat"
if "%OP%"=="2" start "" "https://supabase.com/dashboard"
if "%OP%"=="3" start "" "https://dashboard.render.com/"
if "%OP%"=="4" start "" "%~dp0PUBLICACAO_PASSO_A_PASSO.html"
if "%OP%"=="5" goto migrar
if "%OP%"=="6" exit /b 0
goto menu
:migrar
call "%~dp0MIGRAR_BANCO_SUPABASE.bat"
goto menu
