# Build only. Uses an already installed SDK; no Rhino load/registration.
[CmdletBinding()]
param([string]$OutputDirectory = '', [switch]$RefreshCatalog)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$src=Split-Path $root -Parent
$install=[IO.Path]::GetFullPath((Join-Path $src 'rhp\AlmondRhino'))
$data=Join-Path $root 'data'
New-Item -ItemType Directory -Path $data -Force | Out-Null
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE='false'
$env:DOTNET_NOLOGO='1'
$env:DOTNET_CLI_HOME=Join-Path $data 'dotnet-home'
$sdk=Join-Path $src 'rhp\RhinoTerminal\data\sdk\dotnet.exe'
if(-not (Test-Path -LiteralPath $sdk)) {
    $installed=Get-Command dotnet.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if(-not $installed) { throw 'An installed .NET 8 SDK is required. No SDK will be downloaded automatically.' }
    $sdk=$installed.Source
}
# AlmondRhino output stays at the fixed installation depth; source belongs to src/cos.
if(-not $OutputDirectory) { $OutputDirectory=Join-Path $install 'plugin-runtime' }
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if([IO.Path]::GetDirectoryName($OutputDirectory) -ine $install -or
   [IO.Path]::GetFileName($OutputDirectory) -notlike 'plugin-*') {
    throw 'Output must be a plugin-* directory directly under src/rhp/AlmondRhino.'
}
if(Test-Path -LiteralPath $OutputDirectory) {
    Get-ChildItem -LiteralPath $OutputDirectory -File | Where-Object { $_.Extension -in '.dll','.rhp' } | ForEach-Object {
        try { $probe=[IO.File]::Open($_.FullName,'Open','ReadWrite','None'); $probe.Dispose() }
        catch { throw "Output is in use; close its Rhino normally before building: $($_.FullName)" }
    }
}
$staging=Join-Path $data ('build-'+[guid]::NewGuid().ToString('N'))
& $sdk build (Join-Path $root 'rhp\AlmondRhino.csproj') -c Release -o $staging --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
if($LASTEXITCODE) { throw 'AlmondRhino build failed.' }
if($RefreshCatalog) {
    $python=Join-Path $src 'engine\.venv\Scripts\python.exe'
    & $python -B (Join-Path $src 'cos\build_catalog.py')
    if($LASTEXITCODE) { throw 'AlmondRhino catalog generation failed.' }
}
$previous=Join-Path $data ('previous-build-'+[guid]::NewGuid().ToString('N'))
# Every move/delete target is confined to this checkout's module/install roots.
foreach($path in $staging,$previous) {
    if(-not [IO.Path]::GetFullPath($path).StartsWith([IO.Path]::GetFullPath($data)+'\',[StringComparison]::OrdinalIgnoreCase)) {
        throw 'Build staging escaped the external connector data directory.'
    }
}
if(Test-Path -LiteralPath $OutputDirectory) { Move-Item -LiteralPath $OutputDirectory -Destination $previous }
try { Move-Item -LiteralPath $staging -Destination $OutputDirectory }
catch {
    if(Test-Path -LiteralPath $previous) { Move-Item -LiteralPath $previous -Destination $OutputDirectory }
    throw
}
if(Test-Path -LiteralPath $previous) { Remove-Item -LiteralPath $previous -Recurse -Force }
Write-Host "Built $OutputDirectory\AlmondRhino.rhp and Almond.Engine.dll. No Rhino load or registration was performed."
