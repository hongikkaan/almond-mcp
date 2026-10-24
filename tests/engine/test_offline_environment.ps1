# Check isolation without starting a server or Rhino.
$ErrorActionPreference = 'Stop'
$testRepo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$before = @{}
Get-ChildItem Env: | Where-Object { $_.Name -like 'RHINO_MCP_*' -or $_.Name -in @('TEMP', 'TMP') } |
    ForEach-Object { $before[$_.Name] = $_.Value }
$userDrawing = [Environment]::GetEnvironmentVariable('RHINO_MCP_DRAWING_ASSET_DIR', 'User')
try {
    $env:RHINO_MCP_DRAWING_ASSET_DIR = 'C:\other-checkout\drawing'
    $env:RHINO_MCP_STATE_DB = 'C:\other-checkout\state.sqlite3'
    & (Join-Path $testRepo 'src\engine\use_offline_environment.ps1')
    $library = Join-Path $testRepo 'asset\grasshopper\Grasshopperfiles'
    if (-not (Test-Path -LiteralPath $library -PathType Container)) {
        $library = Join-Path $testRepo 'data\offline\libraries\Grasshopperfiles'
    }
    $expected = @{
        RHINO_MCP_STATE_DB = Join-Path $testRepo 'data\offline\state.sqlite3'
        RHINO_MCP_DRAWING_ASSET_DIR = Join-Path $testRepo 'asset\drawing\DrawingAssetfiles'
        RHINO_MCP_MATERIAL_DIR = Join-Path $testRepo 'asset\constructions\Materialfiles'
        RHINO_MCP_LIBRARY_DIR = $library
        TEMP = Join-Path $testRepo 'data\offline\tmp'
        TMP = Join-Path $testRepo 'data\offline\tmp'
    }
    foreach ($name in $expected.Keys) {
        $actual = [Environment]::GetEnvironmentVariable($name, 'Process')
        if ($actual -ne $expected[$name]) { throw "Wrong offline path: $name" }
    }
    if ([Environment]::GetEnvironmentVariable('RHINO_MCP_DRAWING_ASSET_DIR', 'User') -ne $userDrawing) {
        throw 'Offline setup changed the persistent user environment.'
    }
    Write-Output 'Offline environment isolation checks passed.'
} finally {
    Get-ChildItem Env: | Where-Object { $_.Name -like 'RHINO_MCP_*' -or $_.Name -in @('TEMP', 'TMP') } |
        ForEach-Object { [Environment]::SetEnvironmentVariable($_.Name, $before[$_.Name], 'Process') }
}
