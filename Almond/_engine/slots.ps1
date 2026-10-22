# Shared allocation gate and lifetime slot mutexes. No process is stopped here.
function Enter-AlmondGate {
    $m=New-Object System.Threading.Mutex($false,'Local\Almond_Process_Maintenance')
    $owned=$false
    try {
        try {$owned=$m.WaitOne(2000)} catch [System.Threading.AbandonedMutexException] {$owned=$true}
        if(-not $owned){throw 'Almond 시작 또는 정리가 진행 중입니다. 그 창의 작업이 끝난 뒤 다시 실행하세요.'}
        return $m
    } catch {$m.Dispose();throw}
}

function Test-AlmondSlotAvailable([string]$DataRoot,[string]$Slot) {
    if($Slot.Length -ne 1 -or 'ABCDEFGHIJ'.IndexOf($Slot) -lt 0){throw 'Invalid Almond slot. Use A-J.'}
    $port=5501+'ABCDEFGHIJ'.IndexOf($Slot)
    if(@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object {$_.LocalPort -eq $port}).Count){return $false}
    foreach($name in @('active.json','ready.json')){
        $path=Join-Path (Join-Path $DataRoot $Slot) $name
        if(-not (Test-Path -LiteralPath $path -PathType Leaf)){continue}
        try {
            $r=Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
            if(-not $r.pid){continue}
            $p=Get-Process -Id $r.pid -ErrorAction SilentlyContinue
            if($p -and $p.ProcessName -eq 'Rhino' -and $p.StartTime.ToUniversalTime().Ticks.ToString() -eq $r.process_start_ticks){return $false}
        } catch {return $false} # Unreadable ownership information is not a free slot.
    }
    return $true
}

function Enter-AlmondSlot([string]$DataRoot,[string]$Target='Auto',[bool]$CheckOnly=$false,
                         [string]$MutexPrefix='Local\Almond_Dedicated_CLI_',
                         [ValidateSet('ABCDE','ABCDEFGHIJ')][string]$Slots='ABCDEFGHIJ') {
    if($CheckOnly -and $Target -eq 'Auto'){throw 'CheckOnly requires an explicit slot A-J.'}
    $Target=$Target.ToUpperInvariant()
    if($Target -ne 'AUTO' -and ($Target.Length -ne 1 -or $Slots.IndexOf($Target) -lt 0)){
        throw 'This Rhino host does not support the requested slot.'
    }
    $choices=if($Target -eq 'AUTO'){@($Slots.ToCharArray() | ForEach-Object {$_.ToString()})}else{@($Target)}
    foreach($slot in $choices){
        $m=New-Object System.Threading.Mutex($false,($MutexPrefix+$slot))
        $owned=$false
        $keep=$false
        try {
            try {$owned=$m.WaitOne(0)} catch [System.Threading.AbandonedMutexException] {$owned=$true}
            if($owned -and ($CheckOnly -or (Test-AlmondSlotAvailable $DataRoot $slot))){
                $keep=$true
                return [pscustomobject]@{Target=$slot;Mutex=$m}
            }
        } finally {
            if(-not $keep){if($owned){$m.ReleaseMutex()};$m.Dispose()}
        }
    }
    if($Slots -eq 'ABCDE'){
        throw '이 Rhino의 이전 패널이 지원하는 A–E 연결 자리가 모두 사용 중입니다. 추가 연결은 새 Rhino에서 여세요. 이 Rhino도 10개 슬롯을 사용하려면 작업을 저장한 뒤 이 Rhino만 재시작하세요.'
    }
    throw '사용 가능한 Almond 연결 자리가 없습니다(최대 10개). 완료한 연결에서 /exit 하세요. 외부 실행기로 연 Rhino가 남아 있으면 해당 Rhino도 저장하고 닫으세요.'
}
