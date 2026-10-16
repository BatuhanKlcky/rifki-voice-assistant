# Release AAB + debug APK uretir. JDK 17 gerekir.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

$jdk = Get-ChildItem "$here\.jdk\jdk-17*" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
if ($jdk) {
    $env:JAVA_HOME = $jdk.FullName
    $env:PATH = "$env:JAVA_HOME\bin;" + $env:PATH
    Write-Host "JAVA_HOME=$env:JAVA_HOME"
}

if (-not (Test-Path "$here\keystore\keystore.properties")) {
    Write-Host "Keystore yok; create-keystore.ps1 calistiriliyor..."
    powershell -ExecutionPolicy Bypass -File "$here\keystore\create-keystore.ps1"
}

.\gradlew.bat bundleRelease assembleDebug
Copy-Item "$here\app\build\outputs\bundle\release\app-release.aab" "$here\RIFKI-mobile-release.aab" -Force
Copy-Item "$here\app\build\outputs\apk\debug\app-debug.apk" "$here\RIFKI-mobile-debug.apk" -Force
Write-Host "AAB: $here\RIFKI-mobile-release.aab"
Write-Host "APK: $here\RIFKI-mobile-debug.apk"
