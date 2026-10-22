@echo off
cd /d %~dp0
title Ranking de Gastos

if exist %LOCALAPPDATA%\Programs\Python\Python312\python.exe (
    %LOCALAPPDATA%\Programs\Python\Python312\python.exe server.py
    goto fim
)

py -3 server.py 2>nul
if %errorlevel% equ 0 goto fim

python server.py 2>nul
if %errorlevel% equ 0 goto fim

echo.
echo ======================================================
echo  Python nao foi encontrado no sistema!
echo  Baixe e instale em: https://www.python.org/downloads/
echo ======================================================
echo.

:fim
pause
