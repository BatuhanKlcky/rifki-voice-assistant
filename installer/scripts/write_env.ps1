param(
    [Parameter(Mandatory = $true)][string]$AppDir,
    [Parameter(Mandatory = $true)][string]$ApiKey,
    [string]$Model = "antigravity/gemini-2.5-flash",
    [string]$Url = "http://127.0.0.1:20128/v1/chat/completions"
)

$ErrorActionPreference = "Stop"
$AppDir = $AppDir.TrimEnd("\", "/")
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null

$api = $ApiKey.Trim()
$model = if ($Model.Trim()) { $Model.Trim() } else { "antigravity/gemini-2.5-flash" }
$url = if ($Url.Trim()) { $Url.Trim() } else { "http://127.0.0.1:20128/v1/chat/completions" }
# localhost IPv6 tuzağı
if ($url -match '://localhost([:/]|$)') {
    $url = $url -replace '://localhost', '://127.0.0.1'
}


$content = @"
OMNIROUTE_API_KEY=$api
OMNIROUTE_MODEL=$model
OMNIROUTE_URL=$url
WAKE_WORD=rıfkı
WAKE_WORD_LANGUAGE=tr-TR
STT_LANGUAGE=tr-TR
TTS_ENGINE=piper
PIPER_VOICE=tr_TR-fahrettin-medium
LOG_LEVEL=INFO
MOBILE_BRIDGE_ENABLED=true
MOBILE_BRIDGE_HOST=0.0.0.0
MOBILE_BRIDGE_PORT=8765
MOBILE_BRIDGE_TOKEN=
"@

$envPath = Join-Path $AppDir ".env"
[System.IO.File]::WriteAllText($envPath, $content.Trim() + "`r`n", [System.Text.UTF8Encoding]::new($false))
Write-Host "Wrote $envPath"
