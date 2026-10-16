@echo off
chcp 65001 >nul
title RIFKI baslat

REM Dogru klasor: RIFKI.exe + _internal birlikte olmali
set "EXE=%~dp0dist\RIFKI\RIFKI.exe"
if not exist "%EXE%" set "EXE=%~dp0RIFKI\RIFKI.exe"
if not exist "%EXE%" set "EXE=D:\RIFKI-github\RIFKI\RIFKI.exe"

if not exist "%EXE%" (
    echo RIFKI.exe bulunamadi.
    echo Beklenen: %~dp0dist\RIFKI\RIFKI.exe
    pause
    exit /b 1
)

echo Aciliyor: %EXE%
echo.
echo ONEMLI: Arayuz masaustune sabitlenir, digger pencerelerin ARKASINDA kalir.
echo         Gormek icin Win+D (masaustunu goster).
echo         Sag alttaki tepsi ikonuna sag tik -^> Mobil baglanti / Cikis.
echo.

start "" "%EXE%"
timeout /t 2 /nobreak >nul
exit /b 0
