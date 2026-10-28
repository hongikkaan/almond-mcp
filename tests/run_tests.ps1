# Build disposable integration fixtures before pytest; never build/register an RHP.
[CmdletBinding()]
param([string[]]$TestArgs = @(), [switch]$Development, [string]$DotNet = '')
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
& (Join-Path $repo 'src/mcp/use_offline_environment.ps1') -Development:$Development
$python = if ($Development) {
    Join-Path $repo 'data/development/.venv/Scripts/python.exe'
} else {
    Join-Path $repo 'src/engine/.venv/Scripts/python.exe'
}
if (-not $DotNet) {
    $DotNet = Join-Path $repo 'src/rhp/RhinoTerminal/data/sdk/dotnet.exe'
    if (-not (Test-Path -LiteralPath $DotNet -PathType Leaf)) {
        $installed = Get-Command dotnet.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $installed) { throw 'A .NET SDK is required. Pass its dotnet.exe path with -DotNet.' }
        $DotNet = $installed.Source
    }
}
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
$env:DOTNET_GENERATE_ASPNET_CERTIFICATE = 'false'
$env:DOTNET_NOLOGO = '1'
$env:DOTNET_CLI_HOME = Join-Path $repo 'data/dotnet-home'
$archive = Join-Path $repo 'src/rhp/RhinoAlmondBridge/tests/archive_host'
& $DotNet build (Join-Path $archive 'ArchiveHost.csproj') -c Release --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
if ($LASTEXITCODE) { throw 'ArchiveHost fixture build failed; integration tests did not run.' }
$env:ALMOND_ARCHIVE_TEST_HOST = Join-Path $archive 'bin/Release/net48/ArchiveHost.exe'
if (-not (Test-Path -LiteralPath $env:ALMOND_ARCHIVE_TEST_HOST -PathType Leaf)) {
    throw 'ArchiveHost executable is missing; integration tests did not run.'
}
& $python -B -X utf8 -m pytest -c (Join-Path $repo 'pyproject.toml') $PSScriptRoot @TestArgs
if ($LASTEXITCODE) { throw 'Integration tests failed.' }
