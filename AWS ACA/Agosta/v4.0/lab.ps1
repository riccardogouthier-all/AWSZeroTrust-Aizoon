param(
    [ValidateSet('status', 'start', 'stop')]
    [string]$Action = 'status',
    [ValidateSet('all', 'waf', 'web', 'siem')]
    [string]$Role = 'all',
    [switch]$DryRun
)

$pythonCommand = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonCommand)) {
    $pythonCommand = (Get-Command python -ErrorAction Stop).Source
}
$labArguments = @((Join-Path $PSScriptRoot 'lab.py'), $Action, '--role', $Role)
if ($DryRun) { $labArguments += '--dry-run' }
Push-Location -LiteralPath $PSScriptRoot
try {
    & $pythonCommand @labArguments
    $labExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $labExitCode
