param(
    [string]$KbConf = "./kb.conf"
)

if (-not (Test-Path $KbConf)) {
    Write-Error "kb.conf not found: $KbConf"
    exit 2
}

$allow = $env:ALLOW_CORG_ORIGIN
$schemes = $env:CORS_ALLOW_CUSTM_SCHEME

# Build origin entries (comma-separated)
$originEntries = @()
if ($allow) {
    $allow -split ',' | ForEach-Object {
        $o = $_.Trim()
        if ($o) { $originEntries += "    \"$o\" 1;" }
    }
}

# Build custom-scheme entries (semicolon-separated)
$schemeEntries = @()
if ($schemes) {
    $schemes -split ';' | ForEach-Object {
        $s = $_.Trim().Trim('"')
        if ($s) { $schemeEntries += "    \"~^$s://\" 1;" }
    }
}

# Read file and replace blocks
$text = Get-Content $KbConf -Raw

# Replace CORS map block
$start = '# CORS-MAP-START'
$end = '# CORS-MAP-END'
$pattern = "(?s)$start.*?$end"

$newMap = "$start`n        map \$http_origin \$cors_allowed {`n            default 0;`n"
if ($originEntries.Count -gt 0) { $newMap += ($originEntries -join "`n") + "`n" }
$newMap += "        }`n$end"

$text2 = [regex]::Replace($text, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $newMap })

# Replace custom scheme map content
$customPattern = '(?s)map \$http_origin \$cors_custom_scheme_allowed \{.*?\}'
if ($schemeEntries.Count -gt 0) {
    $newCustom = "map \$http_origin \$cors_custom_scheme_allowed {`n            default 0;`n" + ($schemeEntries -join "`n") + "`n        }"
    $text2 = [regex]::Replace($text2, $customPattern, $newCustom)
}

Set-Content -Path $KbConf -Value $text2 -Force
Write-Host "Updated $KbConf"
