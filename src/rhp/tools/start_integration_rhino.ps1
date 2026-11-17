# Start and verify Rhino and Beyond from this checkout for acceptance.
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$ModelPath
)

$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$model = (Resolve-Path -LiteralPath $ModelPath).ProviderPath
if ([IO.Path]::GetExtension($model) -ine '.3dm' -or -not (Test-Path -LiteralPath $model -PathType Leaf)) {
    throw 'Select a saved Rhino .3dm document.'
}
$rhino = Join-Path $env:ProgramFiles 'Rhino 8\System\Rhino.exe'
if (-not (Test-Path -LiteralPath $rhino -PathType Leaf)) {
    throw "Rhino 8 executable not found: $rhino"
}

. (Join-Path $PSScriptRoot 'runtime_registration.ps1')
. (Join-Path $PSScriptRoot 'integration_rhino_startup.ps1')
$plugins = foreach ($entry in Get-RuntimeRegistration $repo) {
    if (-not (Test-Path -LiteralPath $entry.File -PathType Leaf)) {
        throw "Runtime missing: $($entry.File)"
    }
    $original = & $runtimeRegistry Read $entry.Key 'FileName'
    if ($null -eq $original) { throw "Original runtime registration is missing: $($entry.Key)." }
    [pscustomobject]@{
        Path = $entry.Key
        Name = 'FileName'
        Desired = @{ Kind = 'String'; Value = $entry.File }
        Original = $original
    }
}
$python = Join-Path $repo 'src\engine\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Prepare the worktree Python environment with src/mcp/rebuild_environment.ps1.'
}
$probe = Join-Path $repo 'src\cos\tools\verify_integration_connection.py'
$launcher = Join-Path $repo 'src\cos\tools\launch_integration_rhino.py'
& $python -B -E -X utf8 $probe --check-environment
if ($LASTEXITCODE -ne 0) { throw 'The worktree Beyond environment could not be verified.' }
Write-Host "Rhino integration model: $model"

$snapshot = Join-Path $repo ('data/runtime-integration/' + [guid]::NewGuid().ToString('N') + '/registration.json')
$launch = {
    $launchOutput = & $python -B -E -X utf8 $launcher --rhino $rhino --model $model 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Independent Rhino launch failed: $launchOutput" }
    $launchOutput | ConvertFrom-Json
}
$started = Start-RhinoWithTemporaryRegistration -Changes $plugins -Registry $runtimeRegistry -Launch $launch -Snapshot $snapshot -ModelPath $model

try {
    $connectionJson = & $python -B -E -X utf8 $probe --pid $started.ProcessId --start-ticks $started.StartTicks --model $model
    if ($LASTEXITCODE -ne 0) { throw "Beyond could not verify the test connection to Rhino PID $($started.ProcessId)." }
    $connection = $connectionJson | ConvertFrom-Json
    if (-not (Test-IntegrationRuntimeLoaded $started.Process $started.ProcessId $started.StartTicks $started.RuntimeFiles)) {
        throw "Rhino PID $($started.ProcessId) no longer has the verified runtime."
    }

    [pscustomobject]@{
        RhinoPid = $started.ProcessId
        ModelPath = $model
        LoadedRuntime = $started.RuntimeFiles
        RestoredRegistration = @($plugins | ForEach-Object { $_.Original.Value })
        RegistrationSnapshot = $snapshot
        ProcessEvidence = $started.ProcessEvidence
        Beyond = $connection
    }
} finally {
    $started.Process.Dispose()
}
