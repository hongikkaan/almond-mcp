[CmdletBinding()]
param([string[]]$TestArgs = @(), [switch]$Development, [string]$DotNet = '')
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
& (Join-Path $repo 'src/mcp/use_offline_environment.ps1') -Development:$Development -DotNet $DotNet -RequireDotNet
$sdk = $env:ALMOND_TEST_DOTNET
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_NOLOGO = '1'
$env:DOTNET_CLI_HOME = Join-Path $repo 'data/dotnet-home'
$fixtures = @(
    @{ Project = 'src/rhp/Engine/tests/NativeFixture.csproj'; Output = 'src/rhp/Engine/tests/bin/Release/net8.0-windows/NativeFixture.dll' },
    @{ Project = 'src/rhp/RhinoTerminal/tests/AlmondHostContracts/AlmondHostContracts.csproj'; Output = 'src/rhp/RhinoTerminal/tests/AlmondHostContracts/bin/Release/net8.0-windows/AlmondHostContracts.dll' },
    @{ Project = 'src/cos/tests/PipeFixture.csproj'; Output = 'src/cos/tests/bin/Release/net8.0-windows/PipeFixture.dll' }
)
Push-Location $repo
try {
    foreach ($fixture in $fixtures) {
        & $sdk build $fixture.Project -c Release --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
        if ($LASTEXITCODE) { throw "Fixture build failed: $($fixture.Project)" }
        & $sdk $fixture.Output
        if ($LASTEXITCODE) { throw "Fixture verification failed: $($fixture.Output)" }
    }
} finally { Pop-Location }
$python = if ($Development) { Join-Path $repo 'data/development/.venv/Scripts/python.exe' } else { Join-Path $repo 'src/engine/.venv/Scripts/python.exe' }
$temp = Join-Path $env:TEMP ('cos-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
& $python -B -X utf8 -m pytest -c (Join-Path $repo 'pyproject.toml') (Join-Path $PSScriptRoot 'tests') --basetemp $temp @TestArgs
if ($LASTEXITCODE) { throw 'External connector tests failed.' }
