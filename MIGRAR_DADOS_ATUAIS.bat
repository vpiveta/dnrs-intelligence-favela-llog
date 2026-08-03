@echo off
setlocal
cd /d "%~dp0"
title DNR's Intelligence - Migrar dados atuais

echo =====================================================
echo  MIGRACAO DOS DADOS PARA O DNR INTELLIGENCE
echo =====================================================
echo.
echo Arraste para esta janela a PASTA da versao que voce usa hoje,
echo depois pressione ENTER.
echo.
set /p "ORIGEM=Pasta da versao anterior: "
set "ORIGEM=%ORIGEM:"=%"

if not exist "%ORIGEM%" (
  echo A pasta informada nao existe.
  pause
  exit /b 1
)

if not exist backups mkdir backups
if exist "instance\flip.db" copy /y "instance\flip.db" "backups\flip_antes_migracao_%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%.db" >nul

if exist "%ORIGEM%\instance\flip.db" (
  if not exist instance mkdir instance
  copy /y "%ORIGEM%\instance\flip.db" "instance\flip.db" >nul
  echo Banco copiado com sucesso.
) else (
  echo Nenhum banco encontrado em %ORIGEM%\instance\flip.db
)

if exist "%ORIGEM%\uploads" (
  if not exist uploads mkdir uploads
  xcopy "%ORIGEM%\uploads\*" "uploads\" /E /I /Y >nul
  echo Planilhas e uploads copiados.
)

if exist "%ORIGEM%\backups" (
  if not exist backups mkdir backups
  xcopy "%ORIGEM%\backups\*" "backups\" /E /I /Y >nul
)

echo.
echo Migracao concluida. Agora execute INICIAR_DNR_INTELLIGENCE.bat.
pause
