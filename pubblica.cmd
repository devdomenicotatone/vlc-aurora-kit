@echo off
title Kit VLC Aurora - pubblicazione release
rem Crea l'EXE e pubblica una Release su GitHub. Uso: pubblica.cmd 1.0.0 ["note"]
if "%~1"=="" (
  echo Uso: pubblica.cmd VERSIONE  [note]      esempio: pubblica.cmd 1.0.1
  echo Per creare solo l'EXE senza pubblicare: crea-exe.cmd
  echo.
  pause
  exit /b 1
)
set "PS=powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\pubblica-release.ps1" -Versione %1 %2 %3 %4
echo.
pause
