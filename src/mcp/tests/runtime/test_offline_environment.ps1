# Check isolation without starting a server or Rhino.
[CmdletBinding()]
param([switch]$Development, [string]$DotNet = '')
$ErrorActionPreference = 'Stop'
$testRepo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\..'))
$before = @{}
$environmentNames = @('TEMP', 'TMP', 'PATH', 'ALMOND_TEST_DOTNET')
Get-ChildItem Env: | Where-Object { $_.Name -like 'RHINO_MCP_*' -or $_.Name -in $environmentNames } |
    ForEach-Object { $before[$_.Name] = $_.Value }
$userDrawing = [Environment]::GetEnvironmentVariable('RHINO_MCP_DRAWING_ASSET_DIR', 'User')
$userTemp = [Environment]::GetEnvironmentVariable('TEMP', 'User')
$userTmp = [Environment]::GetEnvironmentVariable('TMP', 'User')
$userPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
try {
    $env:RHINO_MCP_DRAWING_ASSET_DIR = 'C:\other-checkout\drawing'
    $env:RHINO_MCP_STATE_DB = 'C:\other-checkout\state.sqlite3'
    & (Join-Path $testRepo 'src\mcp\use_offline_environment.ps1') -Development:$Development -DotNet $DotNet
    $temporary = $env:TEMP
    $temporaryRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Temp'
    if ((Split-Path $temporary -Parent) -ne $temporaryRoot -or (Split-Path $temporary -Leaf) -notmatch '^am-[0-9a-f]{12}$' -or
        -not (Test-Path -LiteralPath $temporary -PathType Container)) {
        throw 'Offline temporary files must use a short checkout-specific directory.'
    }
    & (Join-Path $testRepo 'src\mcp\use_offline_environment.ps1') -Development:$Development -DotNet $DotNet
    if ($env:TEMP -ne $temporary -or $env:TMP -ne $temporary) {
        throw 'Repeated offline setup changed or nested the temporary directory.'
    }
    if ($DotNet) {
        $sdk = [IO.Path]::GetFullPath($DotNet)
        $sdkPaths = @($env:PATH -split ';' | Where-Object { $_ -eq (Split-Path $sdk -Parent) })
        if ($env:ALMOND_TEST_DOTNET -ne $sdk -or $sdkPaths.Count -ne 1 -or
            ($env:PATH -split ';')[0] -ne (Split-Path $sdk -Parent)) {
            throw 'The selected SDK was not propagated once to child processes.'
        }
    }
    $library = Join-Path $testRepo 'asset\grasshopper\Grasshopperfiles'
    if (-not (Test-Path -LiteralPath $library -PathType Container)) {
        $library = Join-Path $testRepo 'data\offline\libraries\Grasshopperfiles'
    }
    $expected = @{
        RHINO_MCP_STATE_DB = Join-Path $testRepo 'data\offline\state.sqlite3'
        RHINO_MCP_DRAWING_ASSET_DIR = Join-Path $testRepo 'asset\drawing\DrawingAssetfiles'
        RHINO_MCP_MATERIAL_DIR = Join-Path $testRepo 'src\mcp\profiles\material'
        RHINO_MCP_LIBRARY_DIR = $library
        TEMP = $temporary
        TMP = $temporary
    }
    foreach ($name in $expected.Keys) {
        $actual = [Environment]::GetEnvironmentVariable($name, 'Process')
        if ($actual -ne $expected[$name]) { throw "Wrong offline path: $name" }
    }
    if ([Environment]::GetEnvironmentVariable('RHINO_MCP_DRAWING_ASSET_DIR', 'User') -ne $userDrawing) {
        throw 'Offline setup changed the persistent user environment.'
    }
    if ([Environment]::GetEnvironmentVariable('TEMP', 'User') -ne $userTemp -or
        [Environment]::GetEnvironmentVariable('TMP', 'User') -ne $userTmp -or
        [Environment]::GetEnvironmentVariable('PATH', 'User') -ne $userPath) {
        throw 'Offline setup changed persistent user temporary paths.'
    }
    Write-Output 'Offline environment isolation checks passed.'
} finally {
    Get-ChildItem Env: | Where-Object { $_.Name -like 'RHINO_MCP_*' -or $_.Name -in $environmentNames } |
        ForEach-Object { [Environment]::SetEnvironmentVariable($_.Name, $before[$_.Name], 'Process') }
}
