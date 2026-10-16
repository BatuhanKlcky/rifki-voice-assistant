param(
    [Parameter(Mandatory = $true)][string]$OmniDir
)

$ErrorActionPreference = "SilentlyContinue"
# Once kontrol: zaten aciksa cik
try {
    $c = New-Object System.Net.Sockets.TcpClient
    $iar = $c.BeginConnect("127.0.0.1", 20128, $null, $null)
    if ($iar.AsyncWaitHandle.WaitOne(400, $false)) {
        $c.EndConnect($iar) | Out-Null
        $c.Close()
        exit 0
    }
    $c.Close()
} catch {}

$exe = Get-ChildItem -Path $OmniDir -Filter "*.exe" -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match 'omni|route|server|gateway' -or $_.Name -eq 'OmniRoute.exe' } |
    Select-Object -First 1

if (-not $exe) {
    $exe = Get-ChildItem -Path $OmniDir -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
}

if ($exe) {
    Start-Process -FilePath $exe.FullName -WorkingDirectory $exe.DirectoryName -WindowStyle Minimized
    exit 0
}

# npm/node baslat
$pkg = Join-Path $OmniDir "package.json"
if (Test-Path $pkg) {
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm start" -WorkingDirectory $OmniDir -WindowStyle Minimized
    exit 0
}

exit 1
