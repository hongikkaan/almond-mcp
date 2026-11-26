# Exercise startup without a Windows registry or Rhino process.
param([Parameter(Mandatory)][string]$Scratch, [switch]$ReusePid)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../../src/rhp/tools/runtime_registration.ps1')
. (Join-Path $PSScriptRoot '../../src/rhp/tools/integration_rhino_startup.ps1')

$paths = @{}
$changes = @(foreach ($entry in Get-RuntimeRegistration $Scratch) {
    $previous = @{ Kind = 'ExpandString'; Value = "%RHINO_BASE%\$($entry.Name).rhp" }
    $paths[$entry.Key] = $previous
    @{ Path = $entry.Key; Name = 'FileName'; Original = $previous;
       Desired = @{ Kind = 'String'; Value = $entry.File } }
})
$registry = {
    param($Operation, $Path, $Name, $Value)
    if ($Name -ne 'FileName' -or -not $paths.ContainsKey($Path)) { throw 'Unexpected registry value.' }
    switch ($Operation) {
        'Read' { $paths[$Path] }
        'Set' { $paths[$Path] = $Value }
        default { throw "Unexpected registry operation: $Operation" }
    }
}
$child = [pscustomobject]@{
    Id = 2001; StartTime = [DateTime]::UtcNow; HasExited = $false; Disposed = $false
    Modules = @($changes | ForEach-Object { [pscustomobject]@{ FileName = $_.Desired.Value } })
}
$child | Add-Member -MemberType ScriptMethod -Name Refresh -Value {}
$child | Add-Member -MemberType ScriptMethod -Name Dispose -Value { $this.Disposed = $true }
$start = $child.StartTime.Ticks.ToString()
$launch = {
    foreach ($candidate in $changes) {
        if ($paths[$candidate.Path].Value -cne $candidate.Desired.Value) { throw 'The temporary path was not applied.' }
    }
    @{ pid = $child.Id; process_start_ticks = $start }
}
$openProcess = {
    param($ProcessId)
    if ($ProcessId -ne $child.Id) { throw 'Startup opened an unrelated process.' }
    if ($ReusePid) { $child.StartTime = $child.StartTime.AddSeconds(1) }
    $child
}
$model = Join-Path $Scratch 'sample.3dm'
$snapshot = Join-Path $Scratch 'registration.json'
$startupError = $null
try {
    $result = Start-RhinoWithTemporaryRegistration -Changes $changes -Registry $registry -Launch $launch `
        -Snapshot $snapshot -ModelPath $model -OpenProcess $openProcess
} catch { $startupError = $_ }

foreach ($candidate in $changes) {
    $restored = $paths[$candidate.Path]
    if ($restored.Kind -ne 'ExpandString' -or $restored.Value -cne $candidate.Original.Value) {
        throw "Could not restore $($candidate.Path)."
    }
}
$evidence = Get-Content -LiteralPath (Join-Path $Scratch 'process.json') -Raw | ConvertFrom-Json
if ($evidence.pid -ne $child.Id -or $evidence.process_start_ticks -ne $start -or $evidence.model_path -cne $model) {
    throw 'Process evidence did not preserve the launched child identity and model.'
}
if ($ReusePid) {
    if (-not $startupError -or $startupError.Exception.Message -notmatch 'changed identity' -or -not $child.Disposed) {
        throw "Expected to reject a reused PID and dispose its handle, received $startupError."
    }
} elseif ($startupError -or $result.ProcessId -ne $child.Id -or $result.RuntimeFiles.Count -ne 2 -or $child.Disposed) {
    throw "Startup did not return the launched process and its two loaded runtimes: $startupError."
}
