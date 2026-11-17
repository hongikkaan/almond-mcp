# Exercise the integration startup/restore path against an in-memory registry and child process.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Scratch)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
. (Join-Path $repo 'src/rhp/tools/runtime_registration.ps1')
. (Join-Path $repo 'src/rhp/tools/integration_rhino_startup.ps1')

$changes = @(foreach ($entry in Get-RuntimeRegistration $Scratch) {
    @{
        Path = $entry.Key; Name = 'FileName'
        Desired = @{ Kind = 'String'; Value = $entry.File }
        Original = @{ Kind = 'ExpandString'; Value = "%TEMPFIXTURE%\$($entry.Name).rhp" }
    }
})
$registry = {
    param($Operation, $Path, $Name, $Value)
    if ($Name -ne 'FileName') { throw 'Integration changed an unrelated registration.' }
    switch ($Operation) {
        'Read' { $fixtureRegistry.Values[$Path] }
        'Set' { $fixtureRegistry.Values[$Path] = $Value }
        default { throw "Unexpected registry operation: $Operation" }
    }
}
$oldRhino = [pscustomobject]@{ Id = 2000 }
function Get-Process {
    $fixtureRegistry.InventoryCalls++
    $oldRhino
    $child
}
function Start-Sleep([int]$Milliseconds) { }

function New-ProcessFixture([string]$Scenario) {
    $fake = [pscustomobject]@{
        Id = 2001
        StartTime = [DateTime]::UtcNow
        HasExited = $false
        Modules = @()
        Files = @($changes | ForEach-Object { $_.Desired.Value })
        Scenario = $Scenario
        RefreshCount = 0
        Disposed = $false
    }
    $fake | Add-Member -MemberType ScriptMethod -Name Refresh -Value {
        $this.RefreshCount++
        if ($this.RefreshCount -eq 2 -and $this.Scenario -eq 'exit') {
            $this.HasExited = $true
        }
        $this.Modules = @([pscustomobject]@{ FileName = $this.Files[0] })
        if ($this.RefreshCount -ge 2) {
            $this.Modules += [pscustomobject]@{ FileName = $this.Files[1] }
        }
    }
    $fake | Add-Member -MemberType ScriptMethod -Name Dispose -Value { $this.Disposed = $true }
    return $fake
}

foreach ($scenario in 'success', 'exit', 'launch-error', 'lookup-error', 'reused-pid', 'concurrent-registration') {
    $fixtureRegistry = @{ Values = @{}; InventoryCalls = 0 }
    foreach ($change in $changes) { $fixtureRegistry.Values[$change.Path] = $change.Original }
    $child = New-ProcessFixture $scenario
    $replacement = @{ Kind = 'String'; Value = 'C:\other-checkout\RhinoAlmondBridge.rhp' }
    $launch = {
        foreach ($change in $changes) {
            if (-not (Test-RegistrationValue $fixtureRegistry.Values[$change.Path] $change.Desired)) {
                throw 'The candidate was not registered at launch.'
            }
        }
        if ($scenario -eq 'launch-error') { throw 'Fixture process launch failed.' }
        if ($scenario -eq 'concurrent-registration') { $fixtureRegistry.Values[$changes[0].Path] = $replacement }
        [pscustomobject]@{
            pid = $child.Id
            process_start_ticks = $child.StartTime.ToUniversalTime().Ticks.ToString()
        }
    }
    $snapshot = Join-Path $Scratch "$scenario/registration.json"
    $processEvidence = Join-Path (Split-Path $snapshot -Parent) 'process.json'
    $model = Join-Path $Scratch 'fixture.3dm'
    $expectedTicks = $child.StartTime.ToUniversalTime().Ticks.ToString()
    $openProcess = {
        param($ProcessId)
        if ($ProcessId -ne $child.Id) { throw 'Opened a PID unrelated to the launched process.' }
        if (-not (Test-Path -LiteralPath $processEvidence)) { throw 'Process lookup happened before evidence was retained.' }
        if ($scenario -eq 'lookup-error') { throw 'Just-launched fixture process disappeared.' }
        if ($scenario -eq 'reused-pid') { $child.StartTime = $child.StartTime.AddSeconds(1) }
        $child
    }
    $expectedError = @{
        success = ''
        exit = 'exited or changed identity'
        'launch-error' = 'Fixture process launch failed'
        'lookup-error' = 'Just-launched fixture process disappeared'
        'reused-pid' = 'exited or changed identity'
        'concurrent-registration' = 'Registration changed during startup'
    }[$scenario]
    try {
        $result = Start-RhinoWithTemporaryRegistration -Changes $changes -Registry $registry -Launch $launch `
            -Snapshot $snapshot -ModelPath $model -OpenProcess $openProcess
        if ($expectedError) { throw "Fixture $scenario did not fail." }
        if ($result.ProcessId -ne $child.Id -or $child.RefreshCount -ne 2 -or
                $result.RuntimeFiles.Count -ne 2 -or $child.Disposed) {
            throw 'The startup did not retain exactly the newly launched process with both plug-ins.'
        }
    } catch {
        if (-not $expectedError -or $_.Exception.Message -notmatch $expectedError) { throw }
        if ($scenario -in 'exit', 'reused-pid', 'concurrent-registration' -and -not $child.Disposed) {
            throw 'The startup did not release its process handle.'
        }
        if ($scenario -ne 'launch-error' -and
                (-not $_.Exception.Message.Contains("Rhino PID $($child.Id) ($expectedTicks)") -or
                 -not $_.Exception.Message.Contains($processEvidence))) {
            throw 'The error did not identify the independently launched Rhino and its evidence.'
        }
    }
    if ($fixtureRegistry.InventoryCalls -ne 0) { throw 'The startup consulted the inventory of existing Rhino processes.' }
    $saved = Get-Content -LiteralPath $snapshot -Raw | ConvertFrom-Json
    if ($saved.Count -ne 2 -or $saved[0].Original.Kind -ne 'ExpandString' -or $saved[0].Original.Value -ne $changes[0].Original.Value) {
        throw 'The recovery snapshot did not preserve both original registrations and their types.'
    }
    if ($scenario -ne 'launch-error') {
        $identity = Get-Content -LiteralPath $processEvidence -Raw | ConvertFrom-Json
        if ($identity.pid -ne $child.Id -or $identity.process_start_ticks -ne $expectedTicks -or
                $identity.model_path -ne $model -or $identity.runtime_files.Count -ne 2) {
            throw 'The detached process identity, model, or runtime paths were not retained.'
        }
    }
    foreach ($change in $changes) {
        $expected = $change.Original
        if ($scenario -eq 'concurrent-registration' -and $change.Path -eq $changes[0].Path) {
            $expected = $replacement
        }
        if (-not (Test-RegistrationValue $fixtureRegistry.Values[$change.Path] $expected)) {
            throw "Registration did not preserve the correct value for $($change.Path) after $scenario."
        }
    }
}
