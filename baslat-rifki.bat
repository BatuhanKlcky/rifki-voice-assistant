@echo off
chcp 65001 >nul
title RIFKI baslat
cd /d "%~dp0"

set "EXE=%~dp0dist\RIFKI\RIFKI.exe"
if not exist "%EXE%" set "EXE=%~dp0RIFKI\RIFKI.exe"

if exist "%EXE%" (
    echo EXE aciliyor: %EXE%
    echo.
    echo ONEMLI: Arayuz masaustune sabitlenir (Win+D ile gor).
    echo         Tepsi ikonu -^> Mobil baglanti / Cikis.
    echo.
    start "" "%EXE%"
    exit /b 0
)

set "PY=%~dp0venv\Scripts\python.exe"
if exist "%PY%" if exist "%~dp0main.py" (
    echo EXE yok; kaynaktan aciliyor...
    start "RIFKI" "%PY%" "%~dp0main.py"
    exit /b 0
)

echo RIFKI bulunamadi.
pause
exit /b 1
