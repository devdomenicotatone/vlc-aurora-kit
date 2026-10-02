@echo off
title Kit VLC Aurora - installazione
rem Doppio clic per installare e configurare VLC. Opzioni: installa.cmd -SoloVerifica  (anteprima senza modifiche)
set "PS=powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\installa.ps1" %*
echo.
pause
