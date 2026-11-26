[CmdletBinding()]
param(
    [string[]]$TestArgs = @(), [switch]$Development, [string]$DotNet = '',
    [string]$PythonExecutable = '', [string]$ScratchDirectory = '',
    [string]$ReleaseReportDirectory = '',
    [ValidateSet('All', 'Mcp', 'Beyond', 'Native', 'Dot', 'Integration')]
    [string]$Scope = 'All'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$testEnvironment = @{ Development = $Development; DotNet = $DotNet; PythonExecutable = $PythonExecutable; ScratchDirectory = $ScratchDirectory }
function Get-PytestArguments([string]$Suite, [string]$Report) {
    # Preserve the root pytest filter for a full run. A scoped run filters that suite.
    if ($Scope -eq $Suite -or $Suite -eq 'Integration') { $TestArgs }
    if ($ReleaseReportDirectory) { '--junitxml'; Join-Path $ReleaseReportDirectory $Report }
}
foreach ($module in 'Mcp', 'Beyond') {
    if ($Scope -in @('All', $module)) {
        $directory = $module.ToLowerInvariant()
        & (Join-Path $repo "src/$directory/run_tests.ps1") @testEnvironment -TestArgs @(Get-PytestArguments $module "$directory-tests.xml")
    }
}
if ($Scope -in 'All', 'Native') {
    if ($Scope -eq 'Native' -and $TestArgs) { throw 'Native scenarios do not accept pytest arguments.' }
    & (Join-Path $repo 'src/rhp/run_tests.ps1') @testEnvironment
}
if ($Scope -notin 'All', 'Dot', 'Integration') { return }
& (Join-Path $repo 'src/mcp/use_offline_environment.ps1') @testEnvironment -RequireDotNet:($Scope -ne 'Dot')
$python = $env:ALMOND_TEST_PYTHON
if ($Scope -in 'All', 'Dot') {
    $dotArgs = @(Get-PytestArguments 'Dot' 'dot-tests.xml')
    $temp = Join-Path $env:TEMP ('dot-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    & $python -B -X utf8 -m pytest -c (Join-Path $repo 'pyproject.toml') (Join-Path $repo 'src/dots/tests') --basetemp $temp @dotArgs
    if ($LASTEXITCODE) { throw 'Dot client tests failed.' }
    if ($Scope -eq 'Dot') { return }
}
$sdk = $env:ALMOND_TEST_DOTNET
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_NOLOGO = '1'
$env:DOTNET_CLI_HOME = Join-Path $repo 'data/dotnet-home'
$project = Join-Path $repo 'src/rhp/RhinoAlmondBridge/tests/archive_host/ArchiveHost.csproj'
$archiveBuild = Join-Path $env:TEMP ('archive-' + [guid]::NewGuid().ToString('N'))
$previousHost = $env:ALMOND_ARCHIVE_TEST_HOST
New-Item -ItemType Directory -Path $archiveBuild -ErrorAction Stop | Out-Null
Push-Location $repo
try {
    & $sdk build $project -c Release --artifacts-path $archiveBuild --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
    if ($LASTEXITCODE) { throw 'ArchiveHost build failed; integration tests did not run.' }
    $env:ALMOND_ARCHIVE_TEST_HOST = Join-Path $archiveBuild 'bin/ArchiveHost/release/ArchiveHost.exe'
    if (-not (Test-Path -LiteralPath $env:ALMOND_ARCHIVE_TEST_HOST -PathType Leaf)) { throw 'ArchiveHost executable is missing; integration tests did not run.' }
    $integrationArgs = @(Get-PytestArguments 'Integration' 'tests.xml')
    $temp = Join-Path $env:TEMP ('root-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    & $python -B -X utf8 -m pytest -c (Join-Path $repo 'pyproject.toml') $PSScriptRoot --basetemp $temp @integrationArgs
    if ($LASTEXITCODE) { throw 'Integration tests failed.' }
} finally {
    Pop-Location
    $env:ALMOND_ARCHIVE_TEST_HOST = $previousHost
    $target = (Resolve-Path -LiteralPath $archiveBuild).ProviderPath
    if ((Split-Path $target -Parent) -eq (Resolve-Path -LiteralPath $env:TEMP).ProviderPath) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}
