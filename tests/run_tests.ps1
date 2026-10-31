[CmdletBinding()]
param([string[]]$TestArgs = @(), [switch]$Development, [string]$DotNet = '')
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
& (Join-Path $repo 'src/mcp/use_offline_environment.ps1') -Development:$Development -DotNet $DotNet -RequireDotNet
$sdk = $env:ALMOND_TEST_DOTNET
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_NOLOGO = '1'
$env:DOTNET_CLI_HOME = Join-Path $repo 'data/dotnet-home'
$project = Join-Path $repo 'src/rhp/RhinoAlmondBridge/tests/archive_host/ArchiveHost.csproj'
Push-Location $repo
try {
    & $sdk build $project -c Release --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
    if ($LASTEXITCODE) { throw 'ArchiveHost build failed; integration tests did not run.' }
} finally { Pop-Location }
$env:ALMOND_ARCHIVE_TEST_HOST = Join-Path (Split-Path $project -Parent) 'bin/Release/net8.0/ArchiveHost.exe'
if (-not (Test-Path -LiteralPath $env:ALMOND_ARCHIVE_TEST_HOST -PathType Leaf)) { throw 'ArchiveHost executable is missing; integration tests did not run.' }
$python = if ($Development) { Join-Path $repo 'data/development/.venv/Scripts/python.exe' } else { Join-Path $repo 'src/engine/.venv/Scripts/python.exe' }
$temp = Join-Path $env:TEMP ('root-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
& $python -B -X utf8 -m pytest -c (Join-Path $repo 'pyproject.toml') $PSScriptRoot --basetemp $temp @TestArgs
if ($LASTEXITCODE) { throw 'Integration tests failed.' }
