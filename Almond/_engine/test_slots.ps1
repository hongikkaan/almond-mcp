# No Rhino/Codex launch. Fixture files and sleeping test children are removed.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'slots.ps1')
$root=Join-Path (Split-Path $PSScriptRoot -Parent) ('data\_slots_test_'+[Guid]::NewGuid().ToString('N'))
$prefix='Local\Almond_Slot_Test_'+[Guid]::NewGuid().ToString('N')+'_'
$children=@()
$utf8=New-Object System.Text.UTF8Encoding($false)
function Assert($value,[string]$message){if(-not $value){throw $message}}
try {
    New-Item -ItemType Directory -Path (Join-Path $root 'A') -Force | Out-Null
    # Test real availability logic with fake OS observations.
    & {
        function Get-NetTCPConnection {param($State,$ErrorAction) @()}
        function Get-Process {param($Id,$ErrorAction) $null}
        Assert (Test-AlmondSlotAvailable $root 'A') 'Empty slot was not free'
        [IO.File]::WriteAllText((Join-Path $root 'A\active.json'),'{"pid":99,"process_start_ticks":"123"}',$utf8)
        Assert (Test-AlmondSlotAvailable $root 'A') 'Dead PID reserved a slot'
        [IO.File]::WriteAllText((Join-Path $root 'A\active.json'),'{broken',$utf8)
        Assert (-not (Test-AlmondSlotAvailable $root 'A')) 'Malformed record treated as free'
    }
    & {
        function Get-NetTCPConnection {param($State,$ErrorAction) [pscustomobject]@{LocalPort=5501}}
        Assert (-not (Test-AlmondSlotAvailable $root 'A')) 'Occupied port treated as free'
    }
    & {
        function Get-NetTCPConnection {param($State,$ErrorAction) [pscustomobject]@{LocalPort=5510}}
        Assert (-not (Test-AlmondSlotAvailable $root 'J')) 'Port 5510 treated as free'
    }
    & {
        $p=[pscustomobject]@{ProcessName='Rhino';StartTime=[DateTime]::UtcNow}
        [IO.File]::WriteAllText((Join-Path $root 'A\active.json'),('{"pid":99,"process_start_ticks":"'+$p.StartTime.ToUniversalTime().Ticks+'"}'),$utf8)
        function Get-NetTCPConnection {param($State,$ErrorAction) @()}
        function Get-Process {param($Id,$ErrorAction) $p}
        Assert (-not (Test-AlmondSlotAvailable $root 'A')) 'Live Rhino with no listener treated as free'
    }
    & {
        function Test-AlmondSlotAvailable {param($DataRoot,$Slot) $Slot -eq 'C'}
        $r=Enter-AlmondSlot $root 'Auto' $false $prefix
        try {Assert ($r.Target -eq 'C') 'Automatic selection did not skip busy slots'}
        finally {$r.Mutex.ReleaseMutex();$r.Mutex.Dispose()}
    }
    & {
        function Test-AlmondSlotAvailable {param($DataRoot,$Slot) $false}
        $blocked=$false
        try {$r=Enter-AlmondSlot $root 'Auto' $false $prefix} catch {$blocked=$true}
        Assert $blocked 'Full capacity was not rejected'
    }
    & {
        function Test-AlmondSlotAvailable {param($DataRoot,$Slot) $Slot -eq 'F'}
        $r=Enter-AlmondSlot $root 'Auto' $false $prefix
        try {Assert ($r.Target -eq 'F') 'Five occupied slots did not select F'}
        finally {$r.Mutex.ReleaseMutex();$r.Mutex.Dispose()}
        $blocked=$false
        try {$r=Enter-AlmondSlot $root 'Auto' $false $prefix -Slots 'ABCDE'} catch {$blocked=$true}
        Assert $blocked 'A legacy host was allocated an unsupported slot'
    }
    & {
        function Test-AlmondSlotAvailable {param($DataRoot,$Slot) $Slot -eq 'J'}
        $r=Enter-AlmondSlot $root 'Auto' $false $prefix
        try {Assert ($r.Target -eq 'J') 'Last slot J was not available'}
        finally {$r.Mutex.ReleaseMutex();$r.Mutex.Dispose()}
    }
    # Ten separate Windows processes request slots simultaneously. No shared
    # start gate is needed for this stricter per-slot mutex contention check.
    $worker=Join-Path $root 'worker.ps1'
    $source=@'
param($Module,$Root,$Prefix,$Label)
$ErrorActionPreference='Stop'
. $Module
function Test-AlmondSlotAvailable {param($DataRoot,$Slot) $true}
while(-not (Test-Path -LiteralPath (Join-Path $Root 'go'))){Start-Sleep -Milliseconds 25}
$r=Enter-AlmondSlot $Root 'Auto' $false $Prefix
try {
 [IO.File]::WriteAllText((Join-Path $Root ($Label+'.txt')),$r.Target)
 while(-not (Test-Path -LiteralPath (Join-Path $Root 'done'))){Start-Sleep -Milliseconds 25}
} finally {$r.Mutex.ReleaseMutex();$r.Mutex.Dispose()}
'@
    [IO.File]::WriteAllText($worker,$source,$utf8)
    $labels=@(1..10 | ForEach-Object {'worker'+$_})
    foreach($label in $labels){
        $psi=New-Object Diagnostics.ProcessStartInfo
        $psi.FileName=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        $psi.UseShellExecute=$false;$psi.CreateNoWindow=$true
        $psi.Arguments='-NoLogo -NoProfile -NonInteractive -File "'+$worker+'" -Module "'+(Join-Path $PSScriptRoot 'slots.ps1')+'" -Root "'+$root+'" -Prefix "'+$prefix+'" -Label '+$label
        $children += [Diagnostics.Process]::Start($psi)
    }
    [IO.File]::WriteAllText((Join-Path $root 'go'),'go')
    $deadline=[DateTime]::UtcNow.AddSeconds(30)
    while(@($labels | Where-Object {-not (Test-Path -LiteralPath (Join-Path $root ($_+'.txt')))}).Count){
        if([DateTime]::UtcNow -gt $deadline){throw 'Concurrent allocation test timed out'}
        Start-Sleep -Milliseconds 50
    }
    $assigned=@($labels | ForEach-Object {[IO.File]::ReadAllText((Join-Path $root ($_+'.txt')))})
    Assert (($assigned | Sort-Object -Unique) -join '' -eq 'ABCDEFGHIJ') 'Concurrent processes did not receive ten distinct slots'
    & {
        function Test-AlmondSlotAvailable {param($DataRoot,$Slot) $true}
        $blocked=$false
        try {$r=Enter-AlmondSlot $root 'Auto' $false $prefix} catch {$blocked=$true}
        Assert $blocked 'An eleventh concurrent allocation was accepted'
    }
    [IO.File]::WriteAllText((Join-Path $root 'done'),'done')
    foreach($p in $children){Assert ($p.WaitForExit(5000) -and $p.ExitCode -eq 0) 'Worker failed'}
    Write-Host 'Slot checks PASS: existing ownership guards, F/J, legacy host limit, ten real concurrent allocations, eleventh rejected.'
} finally {
    foreach($p in $children){if(-not $p.HasExited){$p.Kill();$p.WaitForExit(5000)|Out-Null};$p.Dispose()}
    $approved=[IO.Path]::GetFullPath((Join-Path (Split-Path $PSScriptRoot -Parent) 'data'))+'\'
    if([IO.Path]::GetFullPath($root).StartsWith($approved,[StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $root)){
        Remove-Item -LiteralPath $root -Recurse -Force
    }
}
