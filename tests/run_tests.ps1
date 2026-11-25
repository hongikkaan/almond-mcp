[CmdletBinding()]
param(
    [string[]]$TestArgs = @(), [switch]$Development, [string]$DotNet = '',
    [string]$PythonExecutable = '', [string]$ScratchDirectory = '',
    [string]$ReleaseReportDirectory = ''
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$testEnvironment = @{ Development = $Development; DotNet = $DotNet; PythonExecutable = $PythonExecutable; ScratchDirectory = $ScratchDirectory }
& (Join-Path $repo 'src/mcp/use_offline_environment.ps1') @testEnvironment -RequireDotNet
if ($ReleaseReportDirectory) {
    & (Join-Path $repo 'src/mcp/run_tests.ps1') @testEnvironment -TestArgs @('-q', '--junitxml', (Join-Path $ReleaseReportDirectory 'mcp-tests.xml'))
    & (Join-Path $repo 'src/beyond/run_tests.ps1') @testEnvironment -TestArgs @('-q', '--junitxml', (Join-Path $ReleaseReportDirectory 'beyond-tests.xml'))
    $panelTests = Get-ChildItem -LiteralPath (Join-Path $repo 'src/rhp/Asset_Panel/tests') -File -Filter '*.test.mjs'
    $panelPaths = @($panelTests | ForEach-Object FullName)
    if (-not $panelPaths.Count) { throw 'Asset Panel tests are missing.' }
    & node --test @panelPaths
    if ($LASTEXITCODE) { throw 'Asset Panel tests failed.' }
    $TestArgs += @('-q', '--junitxml', (Join-Path $ReleaseReportDirectory 'tests.xml'))
}
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
$overlayScratch = Join-Path $env:TEMP ('overlay-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
& $env:ALMOND_ARCHIVE_TEST_HOST --overlay $overlayScratch
if ($LASTEXITCODE -ne 0) { throw 'ArchiveHost overlay verification failed.' }
$python = $env:ALMOND_TEST_PYTHON
$temp = Join-Path $env:TEMP ('root-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
& $python -B -X utf8 -m pytest -c (Join-Path $repo 'pyproject.toml') $PSScriptRoot --basetemp $temp @TestArgs
if ($LASTEXITCODE) { throw 'Integration tests failed.' }
