@echo off
setlocal
cd /d "%~dp0"
title Publicar DNR Intelligence Aprovado
where git >nul 2>nul || (echo Git nao encontrado.& pause & exit /b 1)
python scripts\validate_release.py || (pause & exit /b 1)
git status --short
echo.
set /p MSG=Descricao da atualizacao: 
if "%MSG%"=="" set "MSG=Enterprise 1.1 homologada"
git add .
git commit -m "%MSG%"
git pull --rebase origin main
if errorlevel 1 (
  echo Nao foi possivel sincronizar. Resolva o conflito antes de publicar.
  pause
  exit /b 1
)
git push origin main
if errorlevel 1 (pause & exit /b 1)
echo.
echo Publicado. O Render iniciara o deploy automatico.
start "" "https://dashboard.render.com"
pause
