# Developer maintenance only. Never runs automatically at application startup.
# -Development owns a separate environment and does not stop everyday hosts.
[CmdletBinding()]
param([switch]$Development)
$ErrorActionPreference='Stop'
$environmentPath = if ($Development) { '../../data/development/.venv' } else { '../engine/.venv' }
$runtime=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot $environmentPath))
$python=Join-Path $runtime 'Scripts\python.exe'
$uv=(Get-Command uv -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$repo=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
foreach($process in Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'") {
    if($process.ExecutablePath -and [IO.Path]::GetFullPath($process.ExecutablePath) -ieq [IO.Path]::GetFullPath($python)) {
        throw 'This environment is in use. Use -Development for offline work, or close its hosts before maintenance.'
    }
}
# Read both layouts during migration; never move/delete existing connection data.
if (-not $Development) {
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
# Bootstrap must work before the test suite is installed or collected.
@'
from pathlib import Path
import sys
import almond_mcp

expected = Path(sys.argv[1]).resolve() / "src/mcp/__init__.py"
actual = Path(almond_mcp.__file__).resolve()
assert actual == expected, f"Editable source mismatch: {actual} != {expected}"
'@ | & $python -B - $repo
if($LASTEXITCODE){throw 'Editable source check failed.'}
Write-Output "MCP environment ready: $runtime"
if ($Development) {
    Write-Output 'Offline development only. Use run_tests.ps1 -Development; everyday hosts and registration were not changed.'
} else {
    Write-Output 'Run src/cos/configure.ps1 when setting up COS.'
}
