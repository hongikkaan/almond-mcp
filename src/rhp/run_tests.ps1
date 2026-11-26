[CmdletBinding()]
param(
    [switch]$Development,
    [string]$DotNet = '',
    [string]$PythonExecutable = '',
    [string]$ScratchDirectory = ''
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
& (Join-Path $repo 'src/mcp/use_offline_environment.ps1') -Development:$Development -DotNet $DotNet -RequireDotNet `
    -PythonExecutable $PythonExecutable -ScratchDirectory $ScratchDirectory
$scratchRoot = $env:TEMP
$work = Join-Path $scratchRoot ('rhp-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $work | Out-Null
$previousTemp = $env:TEMP
$previousTmp = $env:TMP

Push-Location $repo
try {
    $env:TEMP = $work
    $env:TMP = $work
    $sdk = $env:ALMOND_TEST_DOTNET
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
    $env:DOTNET_NOLOGO = '1'
    $env:DOTNET_CLI_HOME = Join-Path $repo 'data/dotnet-home'
    $node = Get-Command node.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1
    $artifacts = Join-Path $work 'artifacts'

    foreach ($scenario in @('NativeBehavior', 'CapsuleRecovery')) {
        $project = Join-Path $PSScriptRoot "tests/$scenario/$scenario.csproj"
        & $sdk build $project -c Release --artifacts-path $artifacts --nologo `
            -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
        if ($LASTEXITCODE) { throw "Native test build failed: $scenario" }

        & $sdk (Join-Path $artifacts "bin/$scenario/release/$scenario.dll") (Join-Path $work $scenario)
        if ($LASTEXITCODE) { throw "Native behavior check failed: $scenario" }
    }

    & $env:ALMOND_TEST_PYTHON -B -X utf8 ./src/mcp/features/modeling/PlanSection/tests/test_update_placement.py -v
    if ($LASTEXITCODE) { throw 'PlanSection behavior checks failed.' }

    & $node.Source --test ./src/rhp/Asset_Panel/tests/results_view.test.mjs
    if ($LASTEXITCODE) { throw 'Asset Panel behavior checks failed.' }
}
finally {
    Pop-Location
    $env:TEMP = $previousTemp
    $env:TMP = $previousTmp
    $resolved = (Resolve-Path -LiteralPath $work).ProviderPath
    $prefix = (Resolve-Path -LiteralPath $scratchRoot).ProviderPath.TrimEnd('\') + '\'
    if ($resolved.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
