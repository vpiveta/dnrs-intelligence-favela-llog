@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Atualizar DNR Intelligence no GitHub
color 0A

echo =====================================================
echo  Atualizar GitHub e publicar automaticamente no Render
echo =====================================================
echo.
where git >nul 2>nul
if errorlevel 1 (
  echo ERRO: Git nao encontrado. Instale o Git for Windows.
  pause
  exit /b 1
)

if not exist ".git" git init

git branch -M main
git remote get-url origin >nul 2>nul
if errorlevel 1 (
  git remote add origin https://github.com/vpiveta/flip-enterprise.git
) else (
  git remote set-url origin https://github.com/vpiveta/flip-enterprise.git
)

set /p MSG=Descricao da atualizacao: 
if "%MSG%"=="" set "MSG=Atualizacao DNR Intelligence"

git add .
git status --short
git commit -m "%MSG%"
if errorlevel 1 (
  echo Nenhuma alteracao nova para publicar ou ocorreu um erro no commit.
)
git push -u origin main
if errorlevel 1 (
  echo ERRO ao enviar para o GitHub.
  pause
  exit /b 1
)

echo.
echo Publicacao enviada. O Render iniciara o deploy automatico.
start "" "https://dashboard.render.com/"
pause
