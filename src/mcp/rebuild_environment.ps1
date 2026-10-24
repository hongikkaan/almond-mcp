# Developer maintenance only. Never runs automatically at application startup.
# Run only after closing all Almond Codex/Rhino processes.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$runtime=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../engine/.venv'))
$python=Join-Path $runtime 'Scripts\python.exe'
$uv=(Get-Command uv -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$repo=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
foreach($process in Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'") {
    if($process.ExecutablePath -and [IO.Path]::GetFullPath($process.ExecutablePath) -ieq [IO.Path]::GetFullPath($python)) {
        throw 'Close the COS host and all workers using this environment before maintenance.'
    }
}
# Read both layouts during migration; never move/delete existing connection data.
foreach($stateRoot in 'runtime\data','..\engine\data') {
    foreach($slot in 'A','B','C','D','E','F','G','H','I','J'){
        foreach($name in 'active.json','ready.json'){
            $path=Join-Path $PSScriptRoot "$stateRoot\$slot\$name"
            if(Test-Path -LiteralPath $path){
                $record=Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
                $p=Get-Process -Id $record.pid -ErrorAction SilentlyContinue
                if($p -and $p.StartTime.ToUniversalTime().Ticks.ToString() -eq $record.process_start_ticks){
                    throw 'Close all managed Rhino instances before environment maintenance.'
                }
            }
        }
    }
}
$previousEnvironment=$env:UV_PROJECT_ENVIRONMENT
try {
    $env:UV_PROJECT_ENVIRONMENT=$runtime
    & $uv sync --project $repo --locked --python '3.12.12'
    if($LASTEXITCODE){throw 'uv sync failed. Do not start Almond until repaired.'}
} finally {
    $env:UV_PROJECT_ENVIRONMENT=$previousEnvironment
}
& $uv pip check --python $python
if($LASTEXITCODE){throw 'Dependency check failed.'}
& $python -B (Join-Path $repo 'src\mcp\tests\runtime\test_library_paths.py')
if($LASTEXITCODE){throw 'Editable source/library path check failed.'}
Write-Output 'MCP environment ready. Run src/cos/configure.ps1 when setting up COS.'
