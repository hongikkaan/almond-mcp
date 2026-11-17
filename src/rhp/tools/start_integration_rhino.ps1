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
$plugins = foreach ($entry in Get-RuntimeRegistration $repo) {
    if (-not (Test-Path -LiteralPath $entry.File -PathType Leaf)) {
        throw "Runtime missing: $($entry.File)"
    }
    [pscustomobject]@{
        Key = $entry.Key
        Runtime = $entry.File
        Original = (Get-ItemProperty -LiteralPath $entry.Key -Name FileName).FileName
    }
}
if (Get-Process -Name Rhino -ErrorAction SilentlyContinue) {
    throw 'Close Rhino normally before starting an integration session.'
}
$python = Join-Path $repo 'src\engine\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Prepare the worktree Python environment with src/mcp/rebuild_environment.ps1.'
}
$probe = Join-Path $repo 'src\cos\tools\verify_integration_connection.py'
& $python -B -E -X utf8 $probe --check-environment
if ($LASTEXITCODE -ne 0) { throw 'The worktree Beyond environment could not be verified.' }
Write-Host "Rhino integration model: $model"

$changed = @()
$rhinoPid = $null
try {
    foreach ($plugin in $plugins) {
        Set-ItemProperty -LiteralPath $plugin.Key -Name FileName -Value $plugin.Runtime
        $changed += $plugin
    }

    $shell = New-Object -ComObject Shell.Application
    $arguments = '/runscript="_almondconnect" /nosplash "' + $model + '"'
    $shell.ShellExecute($rhino, $arguments, (Split-Path $model -Parent), 'open', 1)

    # Bridge can load at startup, while AlmondRhino loads on almondconnect.
    # Restore as soon as both assemblies are in the new process.
    $expected = @($plugins.Runtime)
    $timer = [Diagnostics.Stopwatch]::StartNew()
    do {
        $processes = @(Get-Process -Name Rhino -ErrorAction SilentlyContinue)
        if ($processes.Count -gt 1) { throw 'More than one Rhino process appeared.' }
        if ($processes.Count -eq 1) {
            $loaded = @($processes[0].Modules | ForEach-Object FileName)
            $missing = @($expected | Where-Object { $_ -notin $loaded })
            if ($missing.Count -eq 0) {
                $rhinoPid = $processes[0].Id
                $startTicks = $processes[0].StartTime.ToUniversalTime().Ticks.ToString()
                break
            }
        }
        Start-Sleep -Milliseconds 250
    } while ($timer.Elapsed.TotalSeconds -lt 60)
    if (-not $rhinoPid) { throw 'Timed out waiting for Rhino to load both candidate plug-ins.' }
} finally {
    $restoreErrors = foreach ($plugin in $changed) {
        try {
            $current = (Get-ItemProperty -LiteralPath $plugin.Key -Name FileName).FileName
            if ($current -ine $plugin.Runtime -and $current -ine $plugin.Original) {
                throw "Registration changed during startup: $($plugin.Key)"
            }
            if ($current -cne $plugin.Original) {
                Set-ItemProperty -LiteralPath $plugin.Key -Name FileName -Value $plugin.Original
            }
            $restored = (Get-ItemProperty -LiteralPath $plugin.Key -Name FileName).FileName
            if ($restored -cne $plugin.Original) { throw "Could not restore $($plugin.Key)" }
        } catch {
            $_
        }
    }
    if ($restoreErrors) { throw "Rhino registration restoration failed: $($restoreErrors -join ', ')" }
}

$connectionJson = & $python -B -E -X utf8 $probe --pid $rhinoPid --start-ticks $startTicks --model $model
if ($LASTEXITCODE -ne 0) { throw "Beyond could not verify the test connection to Rhino PID $rhinoPid." }
$connection = $connectionJson | ConvertFrom-Json
$process = Get-Process -Id $rhinoPid
$loaded = @($process.Modules | ForEach-Object FileName)
if ($process.StartTime.ToUniversalTime().Ticks.ToString() -ne $startTicks -or
        @($expected | Where-Object { $_ -notin $loaded }).Count) {
    throw "Rhino PID $rhinoPid no longer has the verified process identity and runtime."
}

[pscustomobject]@{
    RhinoPid = $rhinoPid
    ModelPath = $model
    LoadedRuntime = $expected
    RestoredRegistration = @($plugins.Original)
    Beyond = $connection
}
