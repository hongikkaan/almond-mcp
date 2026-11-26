# Build only. Uses an already installed SDK; no Rhino load/registration.
[CmdletBinding()]
param([string]$OutputDirectory = '', [switch]$RefreshCatalog)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$src=Split-Path $root -Parent
. (Join-Path $src 'rhp/tools/build_runtime.ps1')
$install=[IO.Path]::GetFullPath((Join-Path $src 'rhp\AlmondRhino'))
$data=Join-Path $root 'data'
New-Item -ItemType Directory -Path $data -Force | Out-Null
Initialize-RuntimeBuildEnvironment
$env:DOTNET_CLI_HOME=Join-Path $data 'dotnet-home'
$sdk=Join-Path $src 'rhp\RhinoTerminal\data\sdk\dotnet.exe'
if(-not (Test-Path -LiteralPath $sdk)) {
    $installed=Get-Command dotnet.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if(-not $installed) { throw 'An installed .NET 8 SDK is required. No SDK will be downloaded automatically.' }
    $sdk=$installed.Source
}
# AlmondRhino output stays at the fixed installation depth; source belongs to src/beyond.
if(-not $OutputDirectory) { $OutputDirectory=Join-Path $install 'plugin-runtime' }
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
Assert-RuntimeOutputAvailable $OutputDirectory $install
$staging=Join-Path $data ('build-'+[guid]::NewGuid().ToString('N'))
& $sdk build (Join-Path $root 'rhp\AlmondRhino.csproj') -c Release -o $staging --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
if($LASTEXITCODE) { throw 'AlmondRhino build failed.' }
if($RefreshCatalog) {
    $python=Join-Path $src 'engine\.venv\Scripts\python.exe'
    & $python -B (Join-Path $root 'build_catalog.py')
    if($LASTEXITCODE) { throw 'AlmondRhino catalog generation failed.' }
}
Publish-RuntimeBuild $staging $OutputDirectory $install $data
Write-Host "Built $OutputDirectory\AlmondRhino.rhp and Almond.Engine.dll. No Rhino load or registration was performed."
