$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $startedAt = [DateTimeOffset]::UtcNow.ToString('o')
    docker compose --profile test run --rm test-allowed
    if ($LASTEXITCODE -ne 0) { throw 'Allowed client checks failed' }
    docker compose --profile test run --rm test-blocked
    if ($LASTEXITCODE -ne 0) { throw 'Blocked client checks failed' }
    $root = (Get-Location).Path
    docker run --rm --network none --mount "type=bind,source=$root,target=/work,readonly" --workdir /work --entrypoint python3 nw26-firewall:local -m unittest discover -s tests -p test_logger.py
    if ($LASTEXITCODE -ne 0) { throw 'Log decoder checks failed' }
    docker run --rm --network none --mount "type=bind,source=$root,target=/work,readonly" --workdir /work --entrypoint python3 nw26-firewall:local tests/check_logs.py $startedAt
    if ($LASTEXITCODE -ne 0) { throw 'Real firewall log checks failed' }
    $apiImage = docker compose images -q api
    if ($LASTEXITCODE -ne 0 -or -not $apiImage) { throw 'API image not found' }
    docker run --rm --network none --mount "type=bind,source=$root,target=/work,readonly" --entrypoint node $apiImage --test /work/tests/test_api.cjs
    if ($LASTEXITCODE -ne 0) { throw 'API log reader checks failed' }
} finally {
    Pop-Location
}
