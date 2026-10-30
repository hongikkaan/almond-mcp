# Offline fixtures only. Does not register/load an RHP or inspect Rhino documents.
[CmdletBinding()]
param([switch]$Development, [string]$DotNet = '')
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$src=Split-Path $root -Parent
$repo=Split-Path $src -Parent
& (Join-Path $src 'mcp\use_offline_environment.ps1') -Development:$Development -DotNet $DotNet -RequireDotNet
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE='false'
$env:DOTNET_NOLOGO='1'
$env:DOTNET_CLI_HOME=Join-Path $root 'data\dotnet-home'
$sdk=$env:ALMOND_TEST_DOTNET
$engineTests=Join-Path $src 'rhp\Engine\tests'
$cosTests=Join-Path $repo 'src\cos\tests'
& $sdk build (Join-Path $engineTests 'NativeFixture.csproj') -c Release --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
if($LASTEXITCODE) { throw 'Native fixture build failed.' }
& $sdk (Join-Path $engineTests 'bin\Release\net8.0-windows\Almond.NativeFixture.dll')
if($LASTEXITCODE) { throw 'Native fixture verification failed.' }
& $sdk build (Join-Path $cosTests 'HostLifecycle\HostLifecycle.csproj') -c Release --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
if($LASTEXITCODE) { throw 'AlmondRhino lifecycle fixture build failed.' }
& $sdk (Join-Path $cosTests 'HostLifecycle\bin\Release\net8.0-windows\HostLifecycle.dll')
if($LASTEXITCODE) { throw 'AlmondRhino lifecycle verification failed.' }
& $sdk build (Join-Path $cosTests 'PipeFixture.csproj') -c Release --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
if($LASTEXITCODE) { throw 'Pipe fixture build failed.' }
$env:ALMONDRHINO_TEST_DOTNET=$sdk
$python=if ($Development) {
    Join-Path $repo 'data\development\.venv\Scripts\python.exe'
} else {
    Join-Path $src 'engine\.venv\Scripts\python.exe'
}
& $python -B (Join-Path $cosTests 'verify.py')
if($LASTEXITCODE) { throw 'AlmondRhino verification failed.' }
