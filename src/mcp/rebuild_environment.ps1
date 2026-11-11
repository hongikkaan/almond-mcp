# Developer maintenance only. Never runs automatically at application startup.
# -Development owns a separate environment and does not stop everyday hosts.
[CmdletBinding()]
param([switch]$Development, [switch]$VerifyOnly)
$ErrorActionPreference='Stop'
$environmentPath = if ($Development) { '../../data/development/.venv' } else { '../engine/.venv' }
$runtime=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot $environmentPath))
$uv=(Get-Command uv -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$repo=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtimes=@($runtime)
# uv run and repository shells can also use the existing root environment.
# Do not create that optional environment or touch it during development checks.
$rootRuntime=Join-Path $repo '.venv'
if (-not $Development -and (Test-Path -LiteralPath $rootRuntime)) { $runtimes += $rootRuntime }
if (-not $VerifyOnly) {
    # Preflight every target before changing any of them.
    $pythons=@($runtimes | ForEach-Object {
        Join-Path $_ 'Scripts\python.exe'
        Join-Path $_ 'Scripts\pythonw.exe'
    })
    foreach($process in Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'") {
        if($process.ExecutablePath -and $pythons -icontains [IO.Path]::GetFullPath($process.ExecutablePath)) {
            throw "Environment in use: $($process.ExecutablePath) (PID $($process.ProcessId)). Close its client normally, then rerun this command. No environment was changed."
        }
    }
}
# Read both layouts during migration; never move/delete existing connection data.
if (-not $Development -and -not $VerifyOnly) {
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
$previousVirtualEnvironment=$env:VIRTUAL_ENV
$failures=@()
try {
    $env:VIRTUAL_ENV=$null
    foreach($runtime in $runtimes) {
        try {
            $python=Join-Path $runtime 'Scripts\python.exe'
            $env:UV_PROJECT_ENVIRONMENT=$runtime
            if (-not $VerifyOnly) {
                # Refresh this checkout's editable metadata as well as pruning extras.
                & $uv sync --project $repo --locked --python '3.12.12' --reinstall-package almond-mcp
                if($LASTEXITCODE){throw "uv sync failed: $runtime. Do not start Almond until repaired."}
            }
            if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Missing environment: $runtime" }
            & $uv sync --project $repo --locked --python '3.12.12' --check
            if($LASTEXITCODE){throw "Environment differs from uv.lock: $runtime"}
            & $uv pip check --python $python
            if($LASTEXITCODE){throw "Dependency check failed: $runtime"}
            # Read-only checks also work while clients are running.
@'
from pathlib import Path
import importlib.metadata as metadata
import json
import re
import sys
import tomllib
from urllib.parse import urlsplit
from urllib.request import url2pathname
from packaging.requirements import Requirement
import almond_mcp

repo, environment = (Path(value).resolve() for value in sys.argv[1:])
assert sys.version_info[:3] == (3, 12, 12), f"Unexpected Python: {sys.version}"
assert Path(sys.prefix).resolve() == environment, f"Wrong environment: {sys.prefix}"
expected = repo / "src/mcp/__init__.py"
actual = Path(almond_mcp.__file__).resolve()
assert actual == expected, f"Editable source mismatch: {actual} != {expected}"
distributions = list(metadata.distributions())
names = [re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower() for d in distributions]
assert len(names) == len(set(names)), "Duplicate installed distributions"
dist = metadata.distribution("almond-mcp")
direct = json.loads(dist.read_text("direct_url.json") or "{}")
url = urlsplit(direct.get("url", ""))
assert direct.get("dir_info", {}).get("editable") is True, "Expected an editable installation"
assert url.scheme == "file" and url.netloc in {"", "localhost"}, "Unexpected editable source URL"
assert Path(url2pathname(url.path)).resolve() == repo, "Editable belongs to another checkout"
project = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))["project"]
assert dist.version == project["version"], "Stale project version metadata"
assert {Requirement(value) for value in dist.requires or []} == {
    Requirement(value) for value in project["dependencies"]
}, "Stale project dependency metadata"
'@ | & $python -I -B - $repo $runtime
            if($LASTEXITCODE){throw "Editable source/metadata check failed: $runtime"}
            Write-Output "MCP environment verified: $runtime"
        } catch {
            if (-not $VerifyOnly) { throw }
            $failures += $_.Exception.Message
            Write-Warning $_.Exception.Message
        }
    }
} finally {
    $env:UV_PROJECT_ENVIRONMENT=$previousEnvironment
    $env:VIRTUAL_ENV=$previousVirtualEnvironment
}
if ($failures.Count) { throw 'Environment verification failed. Close the affected clients normally, then run this command without -VerifyOnly.' }
if ($VerifyOnly) {
    Write-Output 'All selected environments match uv.lock and this checkout. No installed packages or lockfile were changed.'
} elseif ($Development) {
    Write-Output 'Offline development only. Use run_tests.ps1 -Development; everyday hosts and registration were not changed.'
} else {
    Write-Output 'Run src/cos/configure.ps1 when setting up COS.'
}
