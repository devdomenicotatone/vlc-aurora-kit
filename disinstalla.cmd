@echo off
title Kit VLC Aurora - disinstallazione
rem Doppio clic per togliere il kit e rimettere VLC com'era. Opzioni: disinstalla.cmd -SoloVerifica  (anteprima senza modifiche)
set "PS=powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\disinstalla.ps1" %*
echo.
pause
