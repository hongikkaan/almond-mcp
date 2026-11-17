# Temporary integration registration applies to the returned child process.
function Test-IntegrationRuntimeLoaded($Process, [int]$ProcessId, [string]$StartTicks, [string[]]$RuntimeFiles) {
    $Process.Refresh()
    if ($Process.HasExited -or $Process.Id -ne $ProcessId -or
            $Process.StartTime.ToUniversalTime().Ticks.ToString() -ne $StartTicks) {
        throw "The integration Rhino process $ProcessId exited or changed identity."
    }
    $loaded = @($Process.Modules | ForEach-Object FileName)
    return @($RuntimeFiles | Where-Object { $_ -notin $loaded }).Count -eq 0
}

function Start-RhinoWithTemporaryRegistration {
    param(
        [object[]]$Changes,
        [scriptblock]$Registry,
        [scriptblock]$Launch,
        [string]$Snapshot,
        [string]$ModelPath,
        [scriptblock]$OpenProcess = { param($ProcessId) [Diagnostics.Process]::GetProcessById($ProcessId) }
    )
    $runtimeFiles = @($Changes | ForEach-Object { $_.Desired.Value })
    New-Item -ItemType Directory -Path (Split-Path $Snapshot -Parent) -Force | Out-Null
    ConvertTo-Json -InputObject $Changes -Depth 5 | Set-Content -LiteralPath $Snapshot -Encoding UTF8
    Write-Host "Rhino registration snapshot: $Snapshot"
    $applied = [Collections.Generic.List[object]]::new()
    $process = $null
    $processId = $null
    $startTicks = $null
    $processEvidence = Join-Path (Split-Path $Snapshot -Parent) 'process.json'
    try {
        try {
            foreach ($change in $Changes) {
                $current = & $Registry Read $change.Path $change.Name
                if (-not (Test-RegistrationValue $current $change.Original)) {
                    throw "Registration changed before startup: $($change.Path)."
                }
                if (Test-RegistrationValue $current $change.Desired) { continue }
                $applied.Add($change)
                Set-RegistrationValue $Registry $change $change.Desired
            }

            # The independent launcher reports identity from the held native
            # child handle, before we look up that one specific process.
            $identity = & $Launch
            $processId = [int]$identity.pid
            $startTicks = [string]$identity.process_start_ticks
            if ($processId -le 0 -or $startTicks -notmatch '^[1-9][0-9]{0,18}$') {
                throw 'The independent launcher did not return a valid Rhino process identity.'
            }
            [ordered]@{
                pid = $processId
                process_start_ticks = $startTicks
                model_path = $ModelPath
                runtime_files = $runtimeFiles
            } | ConvertTo-Json | Set-Content -LiteralPath $processEvidence -Encoding UTF8
            Write-Host "Rhino PID $processId ($startTicks). Process evidence: $processEvidence"
            $process = & $OpenProcess $processId
            $timer = [Diagnostics.Stopwatch]::StartNew()
            do {
                $loaded = Test-IntegrationRuntimeLoaded $process $processId $startTicks $runtimeFiles
                if ($loaded) { break }
                Start-Sleep -Milliseconds 250
            } while ($timer.Elapsed.TotalSeconds -lt 60)
            if (-not $loaded) { throw "Timed out waiting for Rhino PID $processId to load both candidate plug-ins." }
        } finally {
            $restoreErrors = @(
                for ($i = $applied.Count - 1; $i -ge 0; $i--) {
                    $change = $applied[$i]
                    try {
                        $current = & $Registry Read $change.Path $change.Name
                        if (Test-RegistrationValue $current $change.Original) { continue }
                        if (-not (Test-RegistrationValue $current $change.Desired)) {
                            throw "Registration changed during startup: $($change.Path)."
                        }
                        Set-RegistrationValue $Registry $change $change.Original
                        $restored = & $Registry Read $change.Path $change.Name
                        if (-not (Test-RegistrationValue $restored $change.Original)) {
                            throw "Could not restore $($change.Path)."
                        }
                    } catch { $_.Exception.Message }
                }
            )
            if ($restoreErrors.Count) {
                throw "Rhino registration restoration failed: $($restoreErrors -join ' ') Snapshot: $Snapshot"
            }
        }
        [pscustomobject]@{
            Process = $process
            ProcessId = $processId
            StartTicks = $startTicks
            RuntimeFiles = $runtimeFiles
            ProcessEvidence = $processEvidence
        }
    } catch {
        if ($null -ne $process) { $process.Dispose() }
        if ($processId -gt 0) {
            throw "Rhino PID $processId ($startTicks): $($_.Exception.Message) Process evidence: $processEvidence"
        }
        throw
    }
}
