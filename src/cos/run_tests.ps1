# Offline fixtures only. Does not register/load an RHP or inspect Rhino documents.
[CmdletBinding()]
param([switch]$Development)
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
if (-not (Test-Path -LiteralPath $python)) { throw 'Run src/mcp/rebuild_environment.ps1 with the same -Development selection first.' }
& $python -B (Join-Path $cosTests 'verify.py')
if($LASTEXITCODE) { throw 'AlmondRhino verification failed.' }
