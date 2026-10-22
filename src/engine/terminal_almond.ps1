# Invoked only by the Rhino Terminal's local almond function. No new Rhino,
# global settings edits, model saves or privilege/approval changes.
[CmdletBinding(PositionalBinding=$false)]
param(
    [Parameter(Mandatory=$true)][string]$PipeName,
    [Parameter(Mandatory=$true)][string]$AccessToken,
    [switch]$CheckOnly,
    [Parameter(Position=0)][string]$Action,
    [Parameter(Position=1)][string]$SessionId
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$lease=$null; $slot=$null; $attached=$false; $previous=@{}
$sharedLeases=@()
$sessionToken=[Guid]::NewGuid().ToString('N')
$utf8=New-Object Text.UTF8Encoding($false)

function Request($Message) {
    $Message.access_token=$AccessToken
    $pipe=New-Object IO.Pipes.NamedPipeClientStream('.', $PipeName, [IO.Pipes.PipeDirection]::InOut, [IO.Pipes.PipeOptions]::Asynchronous)
    try {
        $pipe.Connect(5000)
        $writer=New-Object IO.StreamWriter($pipe,$utf8,1024,$true)
        $reader=New-Object IO.StreamReader($pipe,$utf8,$false,1024,$true)
        try {
            $writer.WriteLine(($Message | ConvertTo-Json -Depth 6 -Compress)); $writer.Flush()
            $read=$reader.ReadLineAsync()
            if(-not $read.Wait(30000)){throw 'Rhino 응답 시간이 초과됐습니다. Rhino의 실행 중인 명령/알림창을 확인하세요.'}
            $answer=$read.Result | ConvertFrom-Json
            if(-not $answer.ok){throw $answer.error}
            return $answer.result
        } finally {$writer.Dispose();$reader.Dispose()}
    } finally {$pipe.Dispose()}
}
function Open-Lease([string]$Path,[switch]$Shared) {
    $share=if($Shared){[IO.FileShare]::ReadWrite}else{[IO.FileShare]::None}
    try {return [IO.File]::Open($Path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,$share)}
    catch {throw "연결 자원이 사용 중이거나 쓸 수 없습니다. 이전 버전의 저장소 연결도 확인하세요: $Path"}
}

try {
    if (($Action -and $Action -ine 'resume') -or ($SessionId -and $Action -ine 'resume')) {
        throw '사용법: almond (새 대화), almond resume (이전 대화 선택), almond resume 세션UUID'
    }
    if ($SessionId -and $SessionId -notmatch '^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$') {
        throw '세션 ID는 오류 메시지나 Codex 종료 화면에 나온 UUID를 입력하세요. 목록은 almond resume.'
    }
    $resume=($Action -ieq 'resume')
    $info=Request @{action='describe'}
    if(-not $info.PSObject.Properties['storage_protocol'] -or $info.storage_protocol -ne 2){
        throw '현재 RhinoTerminal은 공유 저장소 연결을 지원하지 않습니다. 새 플러그인을 등록한 뒤 이 Rhino를 정상 재시작하세요.'
    }
    $python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    . (Join-Path $PSScriptRoot 'slots.ps1')
    # Already loaded 5-slot hosts have no capability field. Keep their requests
    # within A-E until that Rhino is normally restarted; active work is untouched.
    $hostSlots=if($info.PSObject.Properties['supported_slots']){[string]$info.supported_slots}else{'ABCDE'}
    $gate=Enter-AlmondGate
    try {$slot=Enter-AlmondSlot -DataRoot (Join-Path $PSScriptRoot 'data') -Slots $hostSlots}
    finally {$gate.ReleaseMutex();$gate.Dispose()}
    $port=5501+'ABCDEFGHIJ'.IndexOf($slot.Target)
    $raw=& $python -B -X utf8 (Join-Path $PSScriptRoot 'project.py') --model $info.model_path --slot $slot.Target --token $sessionToken --create
    if($LASTEXITCODE -ne 0){throw '공유 저장소의 연결 폴더를 준비하지 못했습니다.'}
    $project=($raw -join "`n") | ConvertFrom-Json
    foreach($name in @('launcher.lock','rhino.lock','mcp.lock')){
        $sharedLeases+=Open-Lease (Join-Path $project.storage $name) -Shared
    }
    $lease=Open-Lease (Join-Path $project.session_dir 'launcher.lock')
    foreach($name in @('rhino.lock','mcp.lock')) {$probe=Open-Lease (Join-Path $project.session_dir $name);$probe.Dispose()}
    $config=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'settings.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    . (Join-Path $PSScriptRoot 'codex_path.ps1')
    $codex=Resolve-AlmondCodex -PreferredPath $config.codex_exe
    # Set the guard before sending: a lost response may still have attached.
    $attached=$true
    $ready=Request @{action='attach';storage_protocol=2;slot=$slot.Target;port=$port;session_token=$sessionToken;
        model_path=$project.model_path;document_serial=$info.document_serial;storage=$project.storage;session_dir=$project.session_dir}
    if($ready.pid -ne $info.pid -or $ready.process_start_ticks -ne $info.process_start_ticks){throw 'Rhino 프로세스가 바뀌었습니다.'}
    if($ready.ready_path -ine $project.ready_path -or $ready.session_dir -ine $project.session_dir){throw '연결 세대의 저장 경로가 다릅니다.'}
    $runtime=@{TERM='xterm-256color';PYTHONUTF8='1';PYTHONIOENCODING='utf-8';PYTHONDONTWRITEBYTECODE='1';
        TEMP=$project.temp;TMP=$project.temp;TMPDIR=$project.temp}
    # Keep shared library selection native. Never replace user AppData/custom
    # sources with the manifests bundled inside this Python environment.
    foreach($key in $runtime.Keys){
        $previous[$key]=[Environment]::GetEnvironmentVariable($key,'Process')
        [Environment]::SetEnvironmentVariable($key,[string]$runtime[$key],'Process')
    }
    Write-Host "Almond 연결: $($project.model_path)"
    Write-Host "DB: $($project.state_db)"
    Write-Host "작업용 출력/TEMP: $($project.temp)"
    Write-Host '연결 중에는 다른 문서를 열거나 이름을 바꾸지 마세요. 끝낼 때 Codex에서 /exit.'
    Write-Host '이전 대화는 /exit 후 PowerShell에서 almond resume. Codex 안의 /resume은 MCP 잠금과 충돌합니다.'
    & (Join-Path $PSScriptRoot 'codex.ps1') -Port $port -AlmondVersion $config.almond_version `
        -RhinoPid $ready.pid -RhinoStartTicks $ready.process_start_ticks -CodexPath $codex `
        -StateDb $project.state_db -WorkDir $project.project_dir `
        -SessionPath $project.ready_path -SessionToken $sessionToken -CheckOnly:$CheckOnly `
        -Resume:$resume -ResumeSessionId $SessionId
    if (-not $CheckOnly) {
        Write-Host '이 패널에서 이어가기: almond resume 또는 almond resume 세션UUID'
    }
} catch {
    Write-Host ("Almond 시작 실패: " + $_.Exception.Message) -ForegroundColor Red
} finally {
    if($attached){
        # Stop returns before an idle listener's accept loop has drained. Retain
        # this launcher's slot and role leases while retrying the same generation.
        $detached=$false
        $detachDeadline=[DateTime]::UtcNow.AddSeconds(10)
        $detachError='Rhino의 남은 작업 또는 MCP 종료를 기다리는 중입니다.'
        do {
            try {
                $detachResult=Request @{action='detach';session_token=$sessionToken}
                $detached=($detachResult.detached -eq $true)
            } catch {$detachError=$_.Exception.Message}
            if(-not $detached){Start-Sleep -Milliseconds 100}
        } while(-not $detached -and [DateTime]::UtcNow -lt $detachDeadline)
        if(-not $detached){Write-Warning ("연결 해제 확인 필요: " + $detachError + ' Rhino 호스트가 자기 잠금을 계속 보유합니다.')}
    }
    foreach($key in $previous.Keys){[Environment]::SetEnvironmentVariable($key,$previous[$key],'Process')}
    if($slot){$slot.Mutex.ReleaseMutex();$slot.Mutex.Dispose()}
    if($lease){$lease.Dispose()}
    foreach($sharedLease in $sharedLeases){$sharedLease.Dispose()}
}
