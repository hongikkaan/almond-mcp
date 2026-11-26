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
$scratch = (Resolve-Path -LiteralPath $env:TEMP).ProviderPath
$work = Join-Path $scratch ('c' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Path $work | Out-Null
$previousTemp = $env:TEMP
$previousTmp = $env:TMP
$previousPipeHost = $env:ALMOND_PIPE_TEST_HOST
$succeeded = $false

try {
    # Keep build artifacts outside pytest's disposable base directory.
    $env:TEMP = $work
    $env:TMP = $work
    $artifacts = Join-Path $work 'a'
    Push-Location $repo
    try {
        & $sdk build src/beyond/tests/PipeFixture.csproj -c Release --artifacts-path $artifacts --nologo `
            -p:UseSharedCompilation=false -p:NuGetAudit=false -nodeReuse:false
        if ($LASTEXITCODE) { throw 'Control pipe fixture build failed.' }
    } finally { Pop-Location }
    $assembly = Join-Path $artifacts 'bin/PipeFixture/release/PipeFixture.dll'
    if (-not (Test-Path -LiteralPath $assembly -PathType Leaf)) {
        throw "Control pipe fixture is missing: $assembly"
    }
    $env:ALMOND_PIPE_TEST_HOST = $assembly

    $temp = Join-Path $work 'p'
    & $env:ALMOND_TEST_PYTHON -B -X utf8 -m pytest -c (Join-Path $repo 'pyproject.toml') (Join-Path $PSScriptRoot 'tests') --basetemp $temp @TestArgs
    if ($LASTEXITCODE) { throw 'External connector tests failed.' }
    $succeeded = $true
}
finally {
    $env:TEMP = $previousTemp
    $env:TMP = $previousTmp
    $env:ALMOND_PIPE_TEST_HOST = $previousPipeHost
    if ($succeeded) {
        $owned = Get-Item -LiteralPath $work
        if ($owned.Parent.FullName -ne $scratch -or ($owned.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Cannot clean up fixture output outside its scratch directory: $work"
        }
        Remove-Item -LiteralPath $owned.FullName -Recurse -Force
    } else {
        Write-Warning "Beyond test work retained at $work"
    }
}
