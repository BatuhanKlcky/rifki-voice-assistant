# RIFKI Setup.exe uretir (PyInstaller + Inno Setup).
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
Set-Location $root

Stop-Process -Name "RIFKI" -Force -ErrorAction SilentlyContinue
Write-Host "Building PyInstaller bundle (rifki.spec)..."
$pyi = Join-Path $root "venv\Scripts\pyinstaller.exe"
if (Test-Path $pyi) {
    & $pyi --noconfirm rifki.spec
} else {
    pyinstaller --noconfirm rifki.spec
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Set-Location $here
$exe = Join-Path $root "dist\RIFKI\RIFKI.exe"
if (-not (Test-Path $exe)) {
    Write-Error "dist\RIFKI\RIFKI.exe olusturulamadi."
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
    Write-Host "Inno Setup 6 kurun: https://jrsoftware.org/isdl.php"
    exit 1
}

Write-Host "ISCC: $iscc"
& $iscc "rifki.iss"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$out = Join-Path $root "dist\RIFKI-Setup-2.6.3.exe"
if (Test-Path $out) {
    Write-Host "OK: $out"
} else {
    Write-Host "Setup uretildi (dist\ klasorune bakin)."
    Get-ChildItem (Join-Path $root "dist") -Filter "RIFKI-Setup*" | Format-Table Name, Length
}
