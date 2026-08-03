[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string] $ScriptName,

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]] $ScriptArgs
)

$ErrorActionPreference = 'Stop'
$scriptFile = if ($ScriptName.EndsWith('.sh', [System.StringComparison]::OrdinalIgnoreCase)) { $ScriptName } else { "$ScriptName.sh" }
$scriptPath = Join-Path $PSScriptRoot $scriptFile
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
    throw "找不到 Bash 腳本：$scriptPath"
}

$wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
if ($wsl) {
    & $wsl.Source -- bash -lc 'command -v bash >/dev/null 2>&1'
    if ($LASTEXITCODE -eq 0) {
        $wslScriptPath = (& $wsl.Source -- wslpath -a $scriptPath 2>$null).Trim()
        if ($LASTEXITCODE -eq 0 -and $wslScriptPath) {
            & $wsl.Source -- bash $wslScriptPath @ScriptArgs
            exit $LASTEXITCODE
        }
    }
}

$gitBashCandidates = @(
    'C:\Program Files\Git\bin\bash.exe',
    'C:\Program Files\Git\usr\bin\bash.exe',
    'C:\Program Files (x86)\Git\bin\bash.exe'
)
$gitBash = $gitBashCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($gitBash) {
    & $gitBash $scriptPath @ScriptArgs
    exit $LASTEXITCODE
}

Write-Error '找不到可執行 Bash 的環境。請先執行 scripts/check-windows-env.ps1。'
exit 1
