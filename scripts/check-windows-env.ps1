$ErrorActionPreference = 'SilentlyContinue'

Write-Output 'Project Cairn Windows environment check'
Write-Output "PowerShell version: $($PSVersionTable.PSVersion)"

$wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
$wslAvailable = $false
if ($wsl) {
    $wslStatus = (& $wsl.Source --status 2>&1 | Out-String).Trim()
    if ($wslStatus) { Write-Output "WSL: available`n$wslStatus" }
    else { Write-Output 'WSL: available' }
    & $wsl.Source -- bash -lc 'command -v bash >/dev/null 2>&1'
    $wslAvailable = ($LASTEXITCODE -eq 0)
    if (-not $wslAvailable) { Write-Output 'WSL: installed, but bash could not be executed' }
} else {
    Write-Output 'WSL: not found'
}

$gitBashCandidates = @(
    'C:\Program Files\Git\bin\bash.exe',
    'C:\Program Files\Git\usr\bin\bash.exe',
    'C:\Program Files (x86)\Git\bin\bash.exe'
)
$gitBash = $gitBashCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($gitBash) { Write-Output "Git Bash: available at $gitBash" }
else { Write-Output 'Git Bash: not found in common installation paths' }

if ($wslAvailable) {
    Write-Output 'Recommendation: use WSL to run the existing Bash scripts.'
    exit 0
}
if ($gitBash) {
    Write-Output 'Recommendation: use Git Bash as a fallback, or install WSL.'
    exit 0
}

Write-Output 'Recommendation: install WSL or Git Bash, then run this check again.'
exit 1
