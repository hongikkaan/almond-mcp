# Build only. Uses an already installed SDK; no Rhino load/registration.
[CmdletBinding()]
param([string]$OutputDirectory = '', [switch]$RefreshCatalog)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$src=Split-Path (Split-Path $root -Parent) -Parent
$data=Join-Path $root 'data'
New-Item -ItemType Directory -Path $data -Force | Out-Null
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE='false'
$env:DOTNET_NOLOGO='1'
$env:DOTNET_CLI_HOME=Join-Path $data 'dotnet-home'
$sdk=Join-Path (Split-Path $root -Parent) 'RhinoTerminal\data\sdk\dotnet.exe'
if(-not (Test-Path -LiteralPath $sdk)) {
    $installed=Get-Command dotnet.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if(-not $installed) { throw 'An installed .NET 8 SDK is required. No SDK will be downloaded automatically.' }
    $sdk=$installed.Source
}
# CosHost resolves the shared Engine and COS data from this plugin directory.
if(-not $OutputDirectory) { $OutputDirectory=Join-Path $root 'plugin-runtime' }
& $sdk build (Join-Path $root 'src\AlmondCOS.csproj') -c Release -o $OutputDirectory --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
if($LASTEXITCODE) { throw 'AlmondCOS build failed.' }
if($RefreshCatalog) {
    $python=Join-Path $src 'engine\.venv\Scripts\python.exe'
    & $python -B (Join-Path $src 'cos\build_catalog.py')
    if($LASTEXITCODE) { throw 'AlmondCOS catalog generation failed.' }
}
Write-Host "Built $OutputDirectory\AlmondCOS.rhp and Almond.Engine.dll. No Rhino load or registration was performed."
