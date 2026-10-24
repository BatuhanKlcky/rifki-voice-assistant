param(
    [Parameter(Mandatory = $true)][string]$AppDir,
    [string]$ApiKey = "",
    [string]$Model = "",
    [string]$Url = ""
)

$ErrorActionPreference = "Stop"
$AppDir = $AppDir.TrimEnd("\", "/")
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null

$envPath = Join-Path $AppDir ".env"

# Mevcut .env'i oku (güncellemede ezme)
$existing = @{}
if (Test-Path $envPath) {
    Get-Content -LiteralPath $envPath -Encoding UTF8 | ForEach-Object {
        $line = $_.TrimEnd()
        if ($line -match '^\s*#' -or $line -match '^\s*$') { return }
        $i = $line.IndexOf("=")
        if ($i -gt 0) {
            $k = $line.Substring(0, $i).Trim()
            $v = $line.Substring($i + 1)
            $existing[$k] = $v
        }
    }
}

function Set-OrKeep([string]$key, [string]$newVal, [string]$fallback) {
    $n = if ($null -eq $newVal) { "" } else { $newVal.Trim() }
    if ($n -ne "") { return $n }
    if ($existing.ContainsKey($key) -and "$($existing[$key])".Trim() -ne "") {
        return "$($existing[$key])".Trim()
    }
    return $fallback
}

$api = Set-OrKeep "OMNIROUTE_API_KEY" $ApiKey ""
$model = Set-OrKeep "OMNIROUTE_MODEL" $Model "antigravity/gemini-2.5-flash"
$url = Set-OrKeep "OMNIROUTE_URL" $Url "http://127.0.0.1:20128/v1/chat/completions"

# Boş anahtarla yazma = güncelleme / sessiz kurulumda mevcut .env'i koru
if ($api -eq "") {
    if (Test-Path $envPath) {
        Write-Host "API key empty; keeping existing .env"
        exit 0
    }
    Write-Host "API key empty and no .env; skip"
    exit 0
}

if ($url -match '://localhost([:/]|$)') {
    $url = $url -replace '://localhost', '://127.0.0.1'
}

# Diğer anahtarları koru (özellikle MOBILE_BRIDGE_TOKEN)
$defaults = [ordered]@{
    "OMNIROUTE_API_KEY"     = $api
    "OMNIROUTE_MODEL"       = $model
    "OMNIROUTE_URL"         = $url
    # ASCII: Türkçe karakter .env encoding bozulmasın (rÄ±fkÄ± hatası)
    "WAKE_WORD"             = (Set-OrKeep "WAKE_WORD" "" "rifki")
    "WAKE_WORD_LANGUAGE"    = (Set-OrKeep "WAKE_WORD_LANGUAGE" "" "tr-TR")
    "STT_LANGUAGE"          = (Set-OrKeep "STT_LANGUAGE" "" "tr-TR")
    "TTS_ENGINE"            = (Set-OrKeep "TTS_ENGINE" "" "piper")
    "PIPER_VOICE"           = (Set-OrKeep "PIPER_VOICE" "" "tr_TR-dfki-medium")
    "LOG_LEVEL"             = (Set-OrKeep "LOG_LEVEL" "" "INFO")
    "MOBILE_BRIDGE_ENABLED" = (Set-OrKeep "MOBILE_BRIDGE_ENABLED" "" "true")
    "MOBILE_BRIDGE_HOST"    = (Set-OrKeep "MOBILE_BRIDGE_HOST" "" "0.0.0.0")
    "MOBILE_BRIDGE_PORT"    = (Set-OrKeep "MOBILE_BRIDGE_PORT" "" "8765")
    "MOBILE_BRIDGE_TOKEN"   = (Set-OrKeep "MOBILE_BRIDGE_TOKEN" "" "")
    "RIFKI_AUTO_UPDATE"    = (Set-OrKeep "RIFKI_AUTO_UPDATE" "" "true")
}

# Mevcut ama defaults'ta olmayan anahtarları da tut
foreach ($k in $existing.Keys) {
    if (-not $defaults.Contains($k)) {
        $defaults[$k] = $existing[$k]
    }
}

$lines = @()
foreach ($k in $defaults.Keys) {
    $lines += "$k=$($defaults[$k])"
}
[System.IO.File]::WriteAllText($envPath, ($lines -join "`r`n") + "`r`n", [System.Text.UTF8Encoding]::new($false))
Write-Host "Wrote $envPath (merged)"
