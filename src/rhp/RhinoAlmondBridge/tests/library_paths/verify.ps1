# Instantiate only managed helper caches from the shipped RHP. No Rhino process,
# plugin registration, document, native geometry call, or library write is used.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RepositoryRoot,
    [Parameter(Mandatory=$true)][string]$PythonExecutable,
    [string]$RhinoSystem = 'C:\Program Files\Rhino 8\System'
)
$ErrorActionPreference = 'Stop'
$runtime = Join-Path $RepositoryRoot 'src/rhp/RhinoAlmondBridge/plugin-runtime'
[void][Reflection.Assembly]::LoadFrom((Join-Path $RhinoSystem 'RhinoCommon.dll'))
[void][Reflection.Assembly]::LoadFrom((Join-Path $runtime 'Newtonsoft.Json.dll'))
$bridge = [Reflection.Assembly]::LoadFrom((Join-Path $runtime 'RhinoAlmondBridge.rhp'))
$engine = [Reflection.Assembly]::LoadFrom((Join-Path $runtime 'Almond.Engine.dll'))
$serverType = $bridge.GetType('RhinoAlmondBridge.BridgeServer', $true)
$validate = $engine.GetType('AlmondEngine.NativeLibraryRoots', $true).GetMethod(
    'Validate', [Reflection.BindingFlags]'Static,NonPublic')
$variables = @('RHINO_MCP_LIBRARY_DIR', 'RHINO_MCP_CAPSULE_DIR', 'RHINO_MCP_DRAWING_ASSET_DIR')
$saved = @{}
foreach ($name in $variables) { $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }

function Get-WorkerLibraries {
    $output = @'
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'src/mcp/runtime'))
from library_paths import configure_library_paths
configure_library_paths()
print(json.dumps({name: os.environ[name] for name in (
    'RHINO_MCP_LIBRARY_DIR', 'RHINO_MCP_CAPSULE_DIR', 'RHINO_MCP_DRAWING_ASSET_DIR')}))
'@ | & $PythonExecutable -B -X utf8 - $RepositoryRoot
    if ($LASTEXITCODE) { throw 'Real worker library configuration failed.' }
    return [System.Text.Json.JsonDocument]::Parse(($output -join "`n"))
}

function Assert-CacheMatchesWorker([string]$scenario) {
    $server = [Activator]::CreateInstance($serverType)
    $worker = Get-WorkerLibraries
    try {
        $validate.Invoke($null, @($server, $worker.RootElement)) | Out-Null
        # A later worker override must still be rejected, without rewriting caches.
        $changed = $worker.RootElement.GetRawText() | ConvertFrom-Json
        $changed.RHINO_MCP_CAPSULE_DIR += '-different-worker'
        $mismatch = [System.Text.Json.JsonDocument]::Parse(($changed | ConvertTo-Json -Compress))
        try {
            $rejected = $false
            try { $validate.Invoke($null, @($server, $mismatch.RootElement)) | Out-Null }
            catch {
                if ($_.Exception.ToString() -notmatch 'loaded native library directory differs.*RHINO_MCP_CAPSULE_DIR') { throw }
                $rejected = $true
            }
            if (-not $rejected) { throw 'A real library override mismatch was accepted.' }
        } finally { $mismatch.Dispose() }
        $validate.Invoke($null, @($server, $worker.RootElement)) | Out-Null
        Write-Output "PASS $scenario; actual native caches match the worker and still reject a changed worker"
    } finally { $worker.Dispose() }
}

try {
    foreach ($name in $variables) { Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue }
    Assert-CacheMatchesWorker 'ordinary Rhino startup without library overrides'
    foreach ($name in $variables) { [Environment]::SetEnvironmentVariable($name, '', 'Process') }
    Assert-CacheMatchesWorker 'empty overrides use the ordinary default'
    foreach ($name in $variables) {
        [Environment]::SetEnvironmentVariable($name,
            (Join-Path ([IO.Path]::GetTempPath()) ('almond-library-contract/custom ' + $name)), 'Process')
    }
    Assert-CacheMatchesWorker 'explicit library overrides are preserved'
} finally {
    foreach ($name in $variables) {
        if ($null -eq $saved[$name]) { Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue }
        else { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
    }
}
