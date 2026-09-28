@echo off
cd /d "%~dp0"
taskkill /f /im appbanco.exe >nul 2>&1
start appbanco.exe

:: Aguarda 20 segundos
timeout /t 20 /nobreak >nul

:: Fecha o navegador (Chrome, Edge ou Firefox)
taskkill /f /im chrome.exe >nul 2>&1
taskkill /f /im msedge.exe >nul 2>&1
taskkill /f /im firefox.exe >nul 2>&1
exit
