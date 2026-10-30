# Run explicitly in a development shell; changes only this process's environment.
[CmdletBinding()]
param([switch]$Development, [string]$DotNet = '', [switch]$RequireDotNet)
$ErrorActionPreference = 'Stop'
$offlineRepo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$environmentPath = if ($Development) { 'data\development\.venv\Scripts\python.exe' } else { 'src\engine\.venv\Scripts\python.exe' }
$offlinePython = Join-Path $offlineRepo $environmentPath
if (-not (Test-Path -LiteralPath $offlinePython)) {
    $prepare = if ($Development) { './src/mcp/rebuild_environment.ps1 -Development' } else { './src/mcp/rebuild_environment.ps1' }
    throw "Python environment not found: $offlinePython. Run $prepare in this checkout first."
}
# Do not derive this from TEMP/TMP: repeated calls must not nest the offline path.
# Native Windows fixtures still need short paths when the checkout is deeply nested.
$offlineTempRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Temp'
$offlineSdk = $null
if ($RequireDotNet -or $DotNet) {
    $candidates = if ($DotNet) { @($DotNet) } else {
        @(Join-Path $offlineRepo 'src/rhp/RhinoTerminal/data/sdk/dotnet.exe') +
        @(Get-Command dotnet.exe -All -CommandType Application -ErrorAction SilentlyContinue | ForEach-Object Source)
    }
    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        # --list-sdks is only inventory; global.json must govern the actual selection.
        Push-Location $offlineRepo
        try { $selectedVersion = & $candidate --version 2>$null }
        finally { Pop-Location }
        if ($LASTEXITCODE -eq 0 -and $selectedVersion -match '^8\.0\.\d+$') {
            $offlineSdk = [IO.Path]::GetFullPath($candidate)
            break
        }
    }
    if (-not $offlineSdk) {
        throw "The .NET 8 SDK is required; a runtime-only dotnet is insufficient. Checked: $($candidates -join ', '). Pass -DotNet <SDK/dotnet.exe>."
    }
}
$offlineJson = @'
import hashlib
import json
import os
from pathlib import Path
import sys
import almond_mcp
from almond_mcp import paths

repo = Path(sys.argv[1]).resolve()
if Path(almond_mcp.__file__).resolve() != repo / "src/mcp/__init__.py":
    raise RuntimeError("The editable environment belongs to another checkout.")
data = repo / "data/offline"
checkout_id = hashlib.sha256(os.fsencode(os.path.normcase(str(repo)))).hexdigest()[:12]
temporary = Path(sys.argv[2]) / ("am-" + checkout_id)
temporary.mkdir(parents=True, exist_ok=True)
environment = {
    "RHINO_MCP_STATE_DB": str(data / "state.sqlite3"),
    "TEMP": str(temporary),
    "TMP": str(temporary),
}
for variable, name in paths.LIBRARY_DIRS.items():
    library = repo / paths.REPO_LIBRARY_PATHS[name]
    if not library.is_dir():
        library = data / "libraries" / name
        library.mkdir(parents=True, exist_ok=True)
    environment[variable] = str(library)
print(json.dumps(environment))
'@ | & $offlinePython -B -X utf8 - $offlineRepo $offlineTempRoot
if ($LASTEXITCODE -ne 0) { throw 'Offline environment preparation failed.' }
$offlineValues = $offlineJson | ConvertFrom-Json
foreach ($entry in $offlineValues.PSObject.Properties) {
    [Environment]::SetEnvironmentVariable($entry.Name, [string]$entry.Value, 'Process')
}
if ($offlineSdk) {
    $env:ALMOND_TEST_DOTNET = $offlineSdk
    $sdkDirectory = Split-Path $offlineSdk -Parent
    $otherPaths = @($env:PATH -split ';' | Where-Object { $_ -and $_ -ne $sdkDirectory })
    $env:PATH = (@($sdkDirectory) + $otherPaths) -join ';'
    Write-Output "Offline test SDK: $offlineSdk ($selectedVersion)"
}
Write-Output "Offline test data: $(Join-Path $offlineRepo 'data\offline')"
Write-Output "Offline temporary files: $($offlineValues.TEMP)"
