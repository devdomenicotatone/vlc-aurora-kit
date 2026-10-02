@echo off
title Kit VLC Aurora - creazione EXE
rem Crea dist\VLC-Aurora-Setup.exe (auto-estraente 7-Zip che avvia installa.cmd). Opzioni: -Versione 1.0.0  -Prova
set "PS=powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\crea-exe.ps1" %*
echo.
pause
