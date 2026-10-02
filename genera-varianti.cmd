@echo off
title Kit VLC Aurora - generazione skin
rem Rigenera le skin precompilate in tutte le scale (serve Python 3 con Pillow). Esempio: genera-varianti.cmd 150
set "PS=powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\genera-varianti.ps1" %*
echo.
pause
