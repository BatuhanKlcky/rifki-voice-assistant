@echo off
cd /d "%~dp0"
echo RIFKI mobil tunnel aciliyor...
echo Once RIFKI'nin acik oldugundan emin ol.
echo.
echo Asagida https://....trycloudflare.com satiri cikacak.
echo Bu adresi telefonda APK Ayarlar ^> Kopru adresine yaz.
echo.
"%~dp0tools\cloudflared.exe" tunnel --url http://127.0.0.1:8765
pause
