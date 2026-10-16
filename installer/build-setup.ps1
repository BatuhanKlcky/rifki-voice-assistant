# RIFKI Setup.exe uretir (Inno Setup gerekli).
# Once: dist\RIFKI\RIFKI.exe olmali (PyInstaller).
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
Set-Location $here

$exe = Join-Path $root "dist\RIFKI\RIFKI.exe"
if (-not (Test-Path $exe)) {
    Write-Error "Once PyInstaller calistir: dist\RIFKI\RIFKI.exe yok. (pyinstaller rifki.spec)"
    exit 1
}

function Find-ISCC {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        (Join-Path $here "tools\InnoSetup\ISCC.exe")
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p)) { return $p }
    }
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

$iscc = Find-ISCC
if (-not $iscc) {
    Write-Host "Inno Setup 6 bulunamadi. Portable indiriliyor..."
    $zipUrl = "https://jrsoftware.org/download.php/is.exe"
    # Offline: kullaniciya net mesaj
    Write-Host ""
    Write-Host "Inno Setup 6 kurun: https://jrsoftware.org/isdl.php"
    Write-Host "Kurulumdan sonra bu scripti tekrar calistirin."
    Write-Host "Veya ISCC.exe yolunu PATH'e ekleyin."
    exit 1
}

Write-Host "ISCC: $iscc"
& $iscc "rifki.iss"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$out = Join-Path $root "dist\RIFKI-Setup-2.1.0.exe"
if (Test-Path $out) {
    Write-Host "OK: $out"
} else {
    Write-Host "Setup uretildi (dist\ klasorune bakin)."
    Get-ChildItem (Join-Path $root "dist") -Filter "RIFKI-Setup*" | Format-Table Name, Length
}
