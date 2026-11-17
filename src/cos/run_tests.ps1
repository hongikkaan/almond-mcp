[CmdletBinding()]
param(
    [string[]]$TestArgs = @(), [switch]$Development, [string]$DotNet = '',
    [string]$PythonExecutable = '', [string]$ScratchDirectory = ''
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
& (Join-Path $repo 'src/mcp/use_offline_environment.ps1') -Development:$Development -DotNet $DotNet -RequireDotNet -PythonExecutable $PythonExecutable -ScratchDirectory $ScratchDirectory
$sdk = $env:ALMOND_TEST_DOTNET
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_NOLOGO = '1'
$env:DOTNET_CLI_HOME = Join-Path $repo 'data/dotnet-home'
$fixtures = @(
    @{ Project = 'src/rhp/Engine/tests/NativeFixture.csproj'; Output = 'src/rhp/Engine/tests/bin/Release/net8.0-windows/NativeFixture.dll' },
    @{ Project = 'src/rhp/Engine/tests/dispatch/DispatchFixture.csproj'; Output = 'src/rhp/Engine/tests/dispatch/bin/Release/net8.0-windows/DispatchFixture.dll'; Scratch = 'dispatch' },
    @{ Project = 'src/rhp/RhinoAlmondBridge/tests/grasshopper/GrasshopperFixture.csproj'; Output = 'src/rhp/RhinoAlmondBridge/tests/grasshopper/bin/Release/net8.0/GrasshopperFixture.dll'; Scratch = 'grasshopper' },
    @{ Project = 'src/rhp/Structural_Analysis/tests/lifetime/AnalysisLifetime.csproj'; Output = 'src/rhp/Structural_Analysis/tests/lifetime/bin/Release/net8.0/AnalysisLifetime.dll' },
    @{ Project = 'src/rhp/RhinoTerminal/tests/AlmondHostContracts/AlmondHostContracts.csproj'; Output = 'src/rhp/RhinoTerminal/tests/AlmondHostContracts/bin/Release/net8.0-windows/AlmondHostContracts.dll' },
    @{ Project = 'src/cos/tests/PipeFixture.csproj'; Output = 'src/cos/tests/bin/Release/net8.0-windows/PipeFixture.dll' }
)
Push-Location $repo
try {
    foreach ($fixture in $fixtures) {
        & $sdk build $fixture.Project -c Release --nologo -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
        if ($LASTEXITCODE) { throw "Fixture build failed: $($fixture.Project)" }
        $fixtureArgs = @()
        if ($fixture.Scratch) { $fixtureArgs += Join-Path $env:TEMP ($fixture.Scratch + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)) }
        & $sdk $fixture.Output @fixtureArgs
        if ($LASTEXITCODE) { throw "Fixture verification failed: $($fixture.Output)" }
    }
} finally { Pop-Location }
$python = $env:ALMOND_TEST_PYTHON
# Session receipt paths include multiple identifiers and an atomic-write suffix.
$temp = Join-Path $env:TEMP ('c' + [guid]::NewGuid().ToString('N').Substring(0, 8))
& $python -B -X utf8 -m pytest -c (Join-Path $repo 'pyproject.toml') (Join-Path $PSScriptRoot 'tests') --basetemp $temp @TestArgs
if ($LASTEXITCODE) { throw 'External connector tests failed.' }
