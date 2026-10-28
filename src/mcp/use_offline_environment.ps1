# Run explicitly in a development shell; changes only this process's environment.
[CmdletBinding()]
param([switch]$Development)
$ErrorActionPreference = 'Stop'
$offlineRepo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$environmentPath = if ($Development) { 'data\development\.venv\Scripts\python.exe' } else { 'src\engine\.venv\Scripts\python.exe' }
$offlinePython = Join-Path $offlineRepo $environmentPath
if (-not (Test-Path -LiteralPath $offlinePython)) {
    throw 'Run src/mcp/rebuild_environment.ps1 with the same -Development selection first.'
}
$offlineJson = @'
import json
from pathlib import Path
import sys
import almond_mcp
from almond_mcp import paths

repo = Path(sys.argv[1]).resolve()
if Path(almond_mcp.__file__).resolve() != repo / "src/mcp/__init__.py":
    raise RuntimeError("The editable environment belongs to another checkout.")
data = repo / "data/offline"
temporary = data / "tmp"
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
'@ | & $offlinePython -B -X utf8 - $offlineRepo
if ($LASTEXITCODE -ne 0) { throw 'Offline environment preparation failed.' }
$offlineValues = $offlineJson | ConvertFrom-Json
foreach ($entry in $offlineValues.PSObject.Properties) {
    [Environment]::SetEnvironmentVariable($entry.Name, [string]$entry.Value, 'Process')
}
Write-Output "Offline test data: $(Join-Path $offlineRepo 'data\offline')"
