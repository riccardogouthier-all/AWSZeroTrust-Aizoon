$ErrorActionPreference = 'Stop'
$pluginDir = Join-Path $PSScriptRoot 'tools/session-manager/package/bin'
if (Test-Path -LiteralPath $pluginDir) { $env:PATH = $pluginDir + ';' + $env:PATH }
if (-not (Get-Command session-manager-plugin -ErrorAction SilentlyContinue)) {
    throw 'Installare il plugin ufficiale AWS Session Manager e aggiungerlo al PATH; vedere README.'
}
$outputs = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'evidence/outputs.json') -Raw | ConvertFrom-Json
if (Get-NetTCPConnection -LocalPort 8443 -State Listen -ErrorAction SilentlyContinue) {
    throw 'La porta locale 8443 è già occupata. Verificare il tunnel esistente.'
}
$arguments = @('ssm', 'start-session', '--region', $outputs.region.value, '--target', $outputs.instances.value.siem.id,
    '--document-name', 'AWS-StartPortForwardingSession', '--parameters', 'portNumber=443,localPortNumber=8443')
$process = Start-Process -FilePath (Get-Command aws).Source -ArgumentList $arguments -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $PSScriptRoot 'evidence/wazuh-tunnel.stdout.txt') `
    -RedirectStandardError (Join-Path $PSScriptRoot 'evidence/wazuh-tunnel.stderr.txt')
$process.Id | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'evidence/wazuh-tunnel.pid')
Write-Output "Tunnel avviato, processo $($process.Id). Dashboard: https://localhost:8443"
