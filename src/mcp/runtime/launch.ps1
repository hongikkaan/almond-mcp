# One start button, up to ten automatic slots. Data belongs to the selected model.
[CmdletBinding()]
param(
    [ValidateSet('Auto','A','B','C','D','E','F','G','H','I','J')][string]$Target='Auto',
    [string]$ModelPath,
    [switch]$PrepareOnly,
    [switch]$CheckOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$slotFolder=$null
$port=0
$utf8=New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding=$utf8
[Console]::OutputEncoding=$utf8
$OutputEncoding=$utf8
$Host.UI.RawUI.WindowTitle='Almond 시작'
$mutex=$null
$owns=$false
$lease=$null
$sharedLeases=@()
$previous=@{}

function Save-Json([string]$Path,$Value){
    $temporary=$Path+'.new-'+[Guid]::NewGuid().ToString('N')
    try {
        [IO.File]::WriteAllText($temporary,($Value|ConvertTo-Json -Depth 8),$utf8)
        if([IO.File]::Exists($Path)){[IO.File]::Replace($temporary,$Path,$null)}
        else {[IO.File]::Move($temporary,$Path)}
    } finally {if([IO.File]::Exists($temporary)){[IO.File]::Delete($temporary)}}
}
function Listeners {
    @(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object {$_.LocalPort -eq $port})
}
function Is-Live($Record){
    if(-not $Record -or -not $Record.pid){return $false}
    $p=Get-Process -Id $Record.pid -ErrorAction SilentlyContinue
    return ($p -and $p.ProcessName -eq 'Rhino' -and
        $p.StartTime.ToUniversalTime().Ticks.ToString() -eq $Record.process_start_ticks)
}
function Confirm-Ready($Ready){
    if($Ready.schema -ne 'almond-project' -or $Ready.label -cne $Target -or [int]$Ready.port -ne $port -or
       $Ready.model_path -ine $project.model_path -or -not (Is-Live $Ready)){
        throw '선택한 파일과 Rhino 연결 정보가 다릅니다. 연결하지 않았습니다.'
    }
    $listeners=@(Listeners)
    if($listeners.Count -ne 1 -or $listeners[0].LocalAddress -ne '127.0.0.1' -or $listeners[0].OwningProcess -ne $Ready.pid){
        throw "Rhino $Target 연결을 확인하지 못했습니다. 해당 Rhino에서 저장한 뒤 Rhino와 Codex를 모두 닫고 다시 시작하세요."
    }
}
function Open-Lease([string]$Path,[switch]$Shared){
    $share=if($Shared){[IO.FileShare]::ReadWrite}else{[IO.FileShare]::None}
    try {return [IO.File]::Open($Path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,$share)}
    catch {throw "연결 자원이 사용 중이거나 쓸 수 없습니다. 공유 저장소를 지원하지 않는 이전 연결도 확인하세요.`n$Path"}
}

try {
    . (Join-Path $PSScriptRoot 'slots.ps1')
    $gate=Enter-AlmondGate
    try {
        $selected=Enter-AlmondSlot -DataRoot (Join-Path $root 'data') -Target $Target -CheckOnly ([bool]$CheckOnly) -Slots 'ABCDEFGHIJ'
        $Target=$selected.Target
        $mutex=$selected.Mutex
        $owns=$true
        $slotFolder=Join-Path $root "data\$Target"
        $port=5501+'ABCDEFGHIJ'.IndexOf($Target)
        $Host.UI.RawUI.WindowTitle="Almond $Target"
        New-Item -ItemType Directory -Path $slotFolder -Force | Out-Null
        $self=Get-Process -Id $PID
        Save-Json (Join-Path $slotFolder 'controller.json') @{
            schema='almond-controller';label=$Target;pid=$PID;
            process_start_ticks=$self.StartTime.ToUniversalTime().Ticks.ToString();engine=$PSScriptRoot}
    } finally {$gate.ReleaseMutex();$gate.Dispose()}
    $config=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'settings.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    . (Join-Path $PSScriptRoot 'codex_path.ps1')
    $config.codex_exe=Resolve-AlmondCodex -PreferredPath $config.codex_exe
    $python=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\engine\.venv\Scripts\python.exe'))
    $native=Join-Path $PSScriptRoot '..\..\rhp\RhinoAlmondBridge\plugin-runtime\Almond.Engine.dll'
    foreach($file in @($config.rhino_exe,$config.codex_exe,$python,$native)){
        if(-not (Test-Path -LiteralPath $file -PathType Leaf)){throw "필수 실행 파일이 없습니다: $file`n이 메시지를 전달해 주세요."}
    }
    $pointerPath=Join-Path $slotFolder 'active.json'
    if($CheckOnly){
        $pointer=Get-Content -LiteralPath $pointerPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if(-not $pointer.PSObject.Properties['storage_protocol'] -or $pointer.storage_protocol -ne 2){
            throw '이전 저장소 연결입니다. 해당 Rhino를 정상 종료한 뒤 새 Almond 연결을 시작하세요.'
        }
        $ModelPath=$pointer.model_path
    } else {
        # Do not adopt a live legacy slot or a model left open after its CLI exited.
        foreach($recordPath in @($pointerPath,(Join-Path $slotFolder 'ready.json'))){
            if(Test-Path -LiteralPath $recordPath){
                $record=Get-Content -LiteralPath $recordPath -Raw -Encoding UTF8 | ConvertFrom-Json
                if(Is-Live $record){throw "Rhino $Target 가 아직 열려 있습니다. 파일을 저장하고 해당 Rhino와 Codex를 모두 닫은 뒤 다시 시작하세요."}
            }
        }
        if(@(Listeners).Count){throw "연결 번호 $port 이 사용 중입니다. 아무 프로그램도 종료하지 않았습니다. 「Almond 시작」을 다시 실행하세요."}
        if(-not $ModelPath){
            Add-Type -AssemblyName System.Windows.Forms
            $picker=New-Object System.Windows.Forms.OpenFileDialog
            try {
                $picker.Title="Almond $Target - 작업할 3dm 선택 (새 모델은 먼저 Rhino에서 저장하세요)"
                $picker.Filter='Rhino 모델 (*.3dm)|*.3dm'
                $picker.CheckFileExists=$true
                $picker.Multiselect=$false
                $picker.RestoreDirectory=$true
                if($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK){return}
                $ModelPath=$picker.FileName
            } finally {$picker.Dispose()}
        }
    }
    $sessionToken=if($CheckOnly){[string]$pointer.token}else{[Guid]::NewGuid().ToString('N')}
    $pathArgs=@('-B','-X','utf8',(Join-Path $PSScriptRoot 'project.py'),'--model',$ModelPath,
        '--slot',$Target,'--token',$sessionToken)
    if(-not $CheckOnly){$pathArgs+='--create'}
    $raw=& $python @pathArgs
    if($LASTEXITCODE -ne 0){throw '저장할 폴더를 준비하지 못했습니다. 위 오류를 전달해 주세요.'}
    $project=($raw -join "`n") | ConvertFrom-Json
    $folder=[string]$project.session_dir
    $readyPath=[string]$project.ready_path
    if(-not $CheckOnly){
        foreach($lockName in @('launcher.lock','rhino.lock','mcp.lock')){
            $sharedLeases+=Open-Lease (Join-Path $project.storage $lockName) -Shared
        }
        $lease=Open-Lease (Join-Path $folder 'launcher.lock')
        $priorLaunch=Join-Path $folder 'launch.json'
        if(Test-Path -LiteralPath $priorLaunch){
            $pending=Get-Content -LiteralPath $priorLaunch -Raw -Encoding UTF8 | ConvertFrom-Json
            if(Is-Live $pending){throw '이 모델의 Rhino가 이미 열려 있거나 시작 중입니다. 해당 Rhino와 Codex를 모두 닫고 다시 시작하세요.'}
        }
        foreach($lockName in @('rhino.lock','mcp.lock')){
            $probe=Open-Lease (Join-Path $folder $lockName)
            $probe.Dispose()
        }
    }
    $runtime=@{TERM='xterm-256color';PYTHONUTF8='1';PYTHONIOENCODING='utf-8';PYTHONDONTWRITEBYTECODE='1';
        ALMOND_PROJECT_ROOT=$project.project_dir}
    # Shared source libraries follow Almond's native resolver: explicit user
    # overrides, then its development checkout or per-user AppData library.
    # DB/tmp are shared by the model directory; wheel data remains only a seed.
    foreach($key in $runtime.Keys){
        $previous[$key]=[Environment]::GetEnvironmentVariable($key,'Process')
        [Environment]::SetEnvironmentVariable($key,[string]$runtime[$key],'Process')
    }
    if($CheckOnly){
        $ready=Get-Content -LiteralPath $readyPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if($ready.token -ne $pointer.token){throw '연결 기록이 바뀌었습니다.'}
    } else {
        # Only current session metadata is replaced. Never delete or infer-migrate an old DB.
        foreach($path in @($readyPath,(Join-Path $folder 'last-error.txt'))){
            if(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $path -Force}
        }
        $launch=@{schema='almond-project';storage_protocol=2;label=$Target;port=$port;token=$sessionToken;
            pid=$null;process_start_ticks='';model_path=$project.model_path;storage=$project.storage;
            temp=$project.temp;session_dir=$folder;ready_path=$readyPath;engine=$PSScriptRoot}
        Save-Json (Join-Path $folder 'launch.json') $launch
        New-Item -ItemType Directory -Path $slotFolder -Force | Out-Null
        $psi=New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName=$config.rhino_exe
        $psi.UseShellExecute=$false
        $psi.WorkingDirectory=$project.project_dir
        $macro='-_RunPythonScript ('+(Join-Path $PSScriptRoot 'rhino_start.py')+')'
        $psi.Arguments='"'+$project.model_path+'" /nosplash /runscript="'+$macro+'"'
        $psi.EnvironmentVariables['ALMOND_SESSION_FOLDER']=$folder
        $psi.EnvironmentVariables['ALMOND_SESSION_TOKEN']=$launch.token
        foreach($old in @('ALMOND_ISOLATED_RUN','ALMOND_V2_RUN','ALMOND_V3_SESSION')){$psi.EnvironmentVariables.Remove($old)}
        Write-Host "Rhino $Target 에서 여는 파일: $($project.model_path)"
        Write-Host "공유 작업 데이터: $($project.storage)"
        $rhino=[System.Diagnostics.Process]::Start($psi)
        $launch.pid=$rhino.Id
        $launch.process_start_ticks=$rhino.StartTime.ToUniversalTime().Ticks.ToString()
        Save-Json (Join-Path $folder 'launch.json') $launch
        Save-Json $pointerPath $launch
        $deadline=[DateTime]::UtcNow.AddMinutes(5)
        while(-not (Test-Path -LiteralPath $readyPath)){
            $errorPath=Join-Path $folder 'last-error.txt'
            if(Test-Path -LiteralPath $errorPath){throw ([IO.File]::ReadAllText($errorPath))}
            if($rhino.HasExited){throw "Rhino $Target 가 시작 중 종료됐습니다. 자동 재시도하지 않았습니다."}
            if([DateTime]::UtcNow -ge $deadline){throw '시작 확인 시간이 초과됐습니다. Rhino의 알림창을 확인하세요. 닫고 재실행하기 전에는 새 작업을 열지 마세요.'}
            Start-Sleep -Milliseconds 250
        }
        $ready=Get-Content -LiteralPath $readyPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if($ready.token -ne $launch.token -or $ready.pid -ne $rhino.Id){throw 'Rhino 시작 정보가 일치하지 않습니다.'}
    }
    Confirm-Ready $ready
    Write-Host "Almond $Target 연결 완료. 저장은 Rhino에서 Ctrl+S. 다른 파일로 바꾸려면 두 창을 닫고 다시 시작하세요."
    if($PrepareOnly){return}
    & (Join-Path $PSScriptRoot 'codex.ps1') -Port $port -AlmondVersion $config.almond_version `
        -RhinoPid $ready.pid -RhinoStartTicks $ready.process_start_ticks -CodexPath $config.codex_exe `
        -StateDb $project.state_db -WorkDir $project.project_dir -SessionPath $readyPath -SessionToken $ready.token -CheckOnly:$CheckOnly
} catch {
    Write-Host "`n시작하지 못했습니다: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    foreach($key in $previous.Keys){[Environment]::SetEnvironmentVariable($key,$previous[$key],'Process')}
    if($lease){$lease.Dispose()}
    foreach($sharedLease in $sharedLeases){$sharedLease.Dispose()}
    if($owns){$mutex.ReleaseMutex()}
    if($mutex){$mutex.Dispose()}
}
