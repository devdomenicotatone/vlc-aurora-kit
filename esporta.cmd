@echo off
title Kit VLC Aurora - esportazione
rem Aggiorna il kit con skin, script e opzioni di questo PC. Opzioni: -Varianti (rigenera le skin), -Push (pubblica su GitHub)
set "PS=powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\esporta.ps1" %*
echo.
pause
