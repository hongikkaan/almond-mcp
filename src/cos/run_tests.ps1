# Offline fixtures only. Does not register/load an RHP or inspect Rhino documents.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$src=Split-Path $root -Parent
$repo=Split-Path $src -Parent
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE='false'
$env:DOTNET_NOLOGO='1'
$env:DOTNET_CLI_HOME=Join-Path $root 'data\dotnet-home'
$sdk=Join-Path $src 'rhp\RhinoTerminal\data\sdk\dotnet.exe'
if(-not (Test-Path -LiteralPath $sdk)) {
    $installed=Get-Command dotnet.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if(-not $installed) { throw 'An installed .NET 8 SDK is required.' }
    $sdk=$installed.Source
}
$native=Join-Path $src 'engine\native'
$engineTests=Join-Path $repo 'tests\engine'
$cosTests=Join-Path $repo 'tests\cos'
& $sdk build (Join-Path $engineTests 'native\NativeFixture.csproj') -c Release --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
if($LASTEXITCODE) { throw 'Native fixture build failed.' }
& $sdk (Join-Path $engineTests 'native\bin\Release\net8.0-windows\Almond.NativeFixture.dll')
if($LASTEXITCODE) { throw 'Native fixture verification failed.' }
& $sdk build (Join-Path $cosTests 'HostLifecycle\HostLifecycle.csproj') -c Release --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
if($LASTEXITCODE) { throw 'COS lifecycle fixture build failed.' }
& $sdk (Join-Path $cosTests 'HostLifecycle\bin\Release\net8.0-windows\HostLifecycle.dll')
if($LASTEXITCODE) { throw 'COS lifecycle verification failed.' }
& $sdk build (Join-Path $cosTests 'PipeFixture.csproj') -c Release --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
if($LASTEXITCODE) { throw 'Pipe fixture build failed.' }
$env:ALMONDCOS_TEST_DOTNET=$sdk
$python=Join-Path $src 'engine\.venv\Scripts\python.exe'
& $python -B (Join-Path $cosTests 'verify.py')
if($LASTEXITCODE) { throw 'AlmondCOS verification failed.' }
