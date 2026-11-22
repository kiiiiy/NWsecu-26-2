param([switch]$Check)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    if (-not (Test-Path -LiteralPath '.env')) {
        $password = [guid]::NewGuid().ToString('N')
        $settings = "ADMIN_CIDRS=172.28.10.100/32`nADMIN_USER=fwadmin`nADMIN_PASSWORD=$password`nHTTP_PORT=80`nSSH_PORT=2222`n"
        [IO.File]::WriteAllText((Join-Path (Get-Location).Path '.env'), $settings, [Text.UTF8Encoding]::new($false))
        Write-Host 'Created .env with a random password and test-admin IP. Add your real administrator source IP before SSH access.'
    }
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Invalid Compose configuration' }
    docker compose up -d --build --wait
    if ($LASTEXITCODE -ne 0) { throw 'Container startup failed. Inspect: docker compose logs' }
    Write-Host 'Web: http://localhost/ (or HTTP_PORT in .env). Logs: logs/firewall.log'
    if ($Check) { & (Join-Path $PSScriptRoot 'check.ps1') }
} finally {
    Pop-Location
}
