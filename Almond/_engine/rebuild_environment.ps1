# Developer maintenance only. Never runs automatically at application startup.
# Run only after closing all Almond Codex/Rhino processes.
[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$runtime=Join-Path $PSScriptRoot '.venv'
$python=Join-Path $runtime 'Scripts\python.exe'
$uv=(Get-Command uv -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$root=Split-Path $PSScriptRoot -Parent
$repo=Split-Path $root -Parent
foreach($process in Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'") {
    if($process.ExecutablePath -and [IO.Path]::GetFullPath($process.ExecutablePath) -ieq [IO.Path]::GetFullPath($python)) {
        throw 'Close the COS host and all workers using this environment before maintenance.'
    }
}
foreach($slot in 'A','B','C','D','E','F','G','H','I','J'){
    foreach($name in 'active.json','ready.json'){
        $path=Join-Path $root "data\$slot\$name"
        if(Test-Path -LiteralPath $path){
            $record=Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
            $p=Get-Process -Id $record.pid -ErrorAction SilentlyContinue
            if($p -and $p.StartTime.ToUniversalTime().Ticks.ToString() -eq $record.process_start_ticks){
                throw 'Close all managed Rhino instances before environment maintenance.'
            }
        }
    }
}
$previousEnvironment=$env:UV_PROJECT_ENVIRONMENT
try {
    $env:UV_PROJECT_ENVIRONMENT=$runtime
    & $uv sync --project $repo --locked --python '3.12.12'
    if($LASTEXITCODE){throw 'uv sync failed. Do not start Almond until repaired.'}
} finally {
    $env:UV_PROJECT_ENVIRONMENT=$previousEnvironment
}
& $uv pip check --python $python
if($LASTEXITCODE){throw 'Dependency check failed.'}
& $python -B (Join-Path $PSScriptRoot 'test_library_paths.py')
if($LASTEXITCODE){throw 'Editable source/library path check failed.'}
& $python -B (Join-Path $repo 'AlmondCOS\build_catalog.py')
if($LASTEXITCODE){throw 'COS catalog generation failed.'}
$cos=@{
    name='Almond COS'
    source=@{kind='command';command=$python;args=@('-B','-u',(Join-Path $repo 'AlmondCOS\cos_host.py'))}
    longestCallSeconds=600
}
$json=$cos | ConvertTo-Json -Depth 4
[IO.File]::WriteAllText((Join-Path $repo 'AlmondCOS\cos-plugin.json'),$json,[Text.UTF8Encoding]::new($false))
