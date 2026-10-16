# Exit 0 = OmniRoute ayakta, 1 = kapali
# Not: localhost yerine 127.0.0.1 (IPv6 ::1 tuzagi)
$ErrorActionPreference = "SilentlyContinue"
$port = 20128
$hostAddr = "127.0.0.1"

try {
    $c = New-Object System.Net.Sockets.TcpClient
    $iar = $c.BeginConnect($hostAddr, $port, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(1500, $false)
    if (-not $ok) { try { $c.Close() } catch {}; exit 1 }
    $c.EndConnect($iar) | Out-Null
    $c.Close()
} catch {
    exit 1
}

# HTTP dogrulama (opsiyonel ama daha dogru)
try {
    $r = Invoke-WebRequest -Uri "http://${hostAddr}:${port}/v1/models" -UseBasicParsing -TimeoutSec 2
    if ($r.StatusCode -ge 200) { exit 0 }
} catch {
    # TCP aciksa yine basarili say (401/404 vs.)
    exit 0
}
exit 0
