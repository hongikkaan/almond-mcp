# The real stage/swap functions run with a fake compiler and archive producer.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Scratch)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
. (Join-Path $repo 'src/rhp/tools/build_runtime.ps1')

function New-StubFile([string]$Path, [string]$Content) {
    New-Item -ItemType Directory -Path (Split-Path $Path -Parent) -Force | Out-Null
    [IO.File]::WriteAllText($Path, $Content)
}
function TestBuildDotNet {
    $output = $args[[array]::IndexOf($args, '-o') + 1]
    if (($args -join ' ') -notmatch 'RestoreLockedMode=true') { throw 'Unlocked Bridge build.' }
    foreach ($name in 'RhinoAlmondBridge.dll', 'RhinoAlmondBridge.deps.json',
                      'RhinoAlmondBridge.runtimeconfig.json', 'RhinoAlmondBridge.pdb', 'Almond.Engine.dll') {
        New-StubFile (Join-Path $output $name) $name
    }
    if ($forbidden) { New-StubFile (Join-Path $output 'RhinoCommon.dll') 'forbidden' }
    $global:LASTEXITCODE = 0
}
function TestBuildPython {
    if ($args.Count -ne 2 -or -not $args[0].EndsWith('build_archive_bundle.py')) { throw 'Unexpected archive invocation.' }
    New-StubFile (Join-Path $args[1] 'bundle.json') 'archive'
    $global:LASTEXITCODE = 0
}

$install = Join-Path $Scratch 'fixed'
$data = Join-Path $Scratch 'staging'
$previousOutput = Join-Path $install 'plugin-runtime'
$daily = Join-Path $data 'daily'
$yakBin = Join-Path $data 'yak-bin'
$yakStage = Join-Path $data 'yak'
$forbidden = $false
New-StubFile (Join-Path $previousOutput 'old.txt') 'old'

Build-BridgeRuntime -Repo $repo -DotNet 'TestBuildDotNet' -Python 'TestBuildPython' -BuildOutput $daily -Staging $daily
Build-BridgeRuntime -Repo $repo -DotNet 'TestBuildDotNet' -Python 'TestBuildPython' -BuildOutput $yakBin -Staging $yakStage
$shared = @('RhinoAlmondBridge.rhp', 'Almond.Engine.dll', 'RhinoAlmondBridge.deps.json',
            'RhinoAlmondBridge.runtimeconfig.json', 'archive/bundle.json', 'LICENSE',
            'THIRD-PARTY-NOTICES.md', 'licenses/xterm-LICENSE.txt')
foreach ($name in $shared) {
    $dailyFile = Join-Path $daily $name
    $yakFile = Join-Path $yakStage $name
    if ((Get-FileHash -LiteralPath $dailyFile).Hash -ne (Get-FileHash -LiteralPath $yakFile).Hash) {
        throw "Bridge staging policies diverged at $name."
    }
}
foreach ($name in 'RhinoAlmondBridge.dll', 'RhinoAlmondBridge.pdb') {
    if (-not (Test-Path -LiteralPath (Join-Path $daily $name)) -or (Test-Path -LiteralPath (Join-Path $yakStage $name))) {
        throw "Unexpected staging policy for $name."
    }
}
$forbidden = $true
try {
    Build-BridgeRuntime -Repo $repo -DotNet 'TestBuildDotNet' -Python 'TestBuildPython' -BuildOutput $yakBin -Staging (Join-Path $data 'forbidden-yak')
    throw 'Yak staging included SDK assemblies.'
} catch {
    if ($_.Exception.Message -notmatch 'Forbidden runtime dependency: RhinoCommon.dll') { throw }
}

$moveCounter = @{ Count = 0 }
function Move-Item([string]$LiteralPath, [string]$Destination) {
    if (++$moveCounter.Count -eq 2) { throw 'Injected staging move failure.' }
    Microsoft.PowerShell.Management\Move-Item @PSBoundParameters
}
try {
    Publish-RuntimeBuild $daily $previousOutput $install $data
    throw 'Expected staging move failure.'
} catch {
    if ($_.Exception.Message -ne 'Injected staging move failure.') { throw }
}
if ((Get-Content -LiteralPath (Join-Path $previousOutput 'old.txt')) -ne 'old') {
    throw 'Previous runtime was lost.'
}
Publish-RuntimeBuild $daily $previousOutput $install $data
if ((Test-Path -LiteralPath $daily) -or (Test-Path -LiteralPath (Join-Path $previousOutput 'old.txt'))) {
    throw 'Successful staging swap left old payload files.'
}
foreach ($name in $shared) {
    if (-not (Test-Path -LiteralPath (Join-Path $previousOutput $name) -PathType Leaf)) {
        throw "Published runtime is missing $name."
    }
}
