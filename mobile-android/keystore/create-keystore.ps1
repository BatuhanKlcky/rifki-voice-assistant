# Release keystore olusturur. keystore/ klasoru gitignore'dadir.
# Kullanim: PowerShell'de bu scripti calistirin.

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

$store = Join-Path $here "rifki-release.jks"
$props = Join-Path $here "keystore.properties"

if (Test-Path $store) {
    Write-Host "Zaten var: $store"
    exit 0
}

$password = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
$keytool = $null
if ($env:JAVA_HOME) {
    $candidate = Join-Path $env:JAVA_HOME "bin\keytool.exe"
    if (Test-Path $candidate) { $keytool = $candidate }
}
if (-not $keytool) {
    $cmd = Get-Command keytool -ErrorAction SilentlyContinue
    if ($cmd) { $keytool = $cmd.Source }
}
if (-not $keytool) {
    $studio = @(
        "$env:LOCALAPPDATA\Programs\Android\Android Studio\jbr\bin\keytool.exe",
        "$env:ProgramFiles\Android\Android Studio\jbr\bin\keytool.exe",
        "C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe",
        "C:\Program Files\Java\*\bin\keytool.exe"
    )
    foreach ($p in $studio) {
        $found = Get-Item $p -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { $keytool = $found.FullName; break }
    }
}
if (-not $keytool) {
    Write-Error "keytool bulunamadi. JAVA_HOME veya Android Studio JBR kurun."
    exit 1
}
Write-Host "keytool: $keytool"


& $keytool -genkeypair `
    -keystore $store `
    -alias rifki `
    -keyalg RSA `
    -keysize 2048 `
    -validity 10000 `
    -storepass $password `
    -keypass $password `
    -dname "CN=RIFKI, OU=Mobile, O=RIFKI, L=Istanbul, ST=Istanbul, C=TR"

@"
storePassword=$password
keyPassword=$password
keyAlias=rifki
storeFile=keystore/rifki-release.jks
"@ | Set-Content -Path $props -Encoding ASCII

Write-Host "Olusturuldu: $store"
Write-Host "Ayarlar: $props"
Write-Host "SIFREYI YEDEKLEYIN - kaybolursa Play guncellemesi imzalanamaz."
