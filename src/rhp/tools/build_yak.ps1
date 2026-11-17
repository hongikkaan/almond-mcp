# Fresh isolated build. Does not install or publish anything.
[CmdletBinding()]
param(
    [string]$PythonExecutable = "python",
    [string]$YakExecutable = "C:\Program Files\Rhino 8\System\Yak.exe",
    [string]$DotnetExecutable = "",
    [string]$RhinoSystem = "C:\Program Files\Rhino 8\System",
    [string]$OutputDirectory = "dist/yak"
)
$ErrorActionPreference = "Stop"
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
. (Join-Path $PSScriptRoot 'build_runtime.ps1')
Initialize-RuntimeBuildEnvironment
if (-not $DotnetExecutable) {
    $checkoutSdk = Join-Path $repo 'src/rhp/RhinoTerminal/data/sdk/dotnet.exe'
    $DotnetExecutable = if (Test-Path -LiteralPath $checkoutSdk -PathType Leaf) { $checkoutSdk } else { 'dotnet' }
}
$rhinoVersion = [Reflection.AssemblyName]::GetAssemblyName((Join-Path $RhinoSystem "RhinoCommon.dll")).Version
if ($rhinoVersion.Major -ne 8) { throw "Expected the installed Rhino 8 SDK." }
$rhinoTag = "rh8_$($rhinoVersion.Minor)"
$stageRoot = Join-Path $repo ("data/t/yak-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$stage = Join-Path $stageRoot "package"
$bin = Join-Path $stageRoot "build"
New-Item -ItemType Directory -Path $stage -Force | Out-Null
if (-not (Test-Path -LiteralPath $YakExecutable)) { throw "Yak executable not found: $YakExecutable" }
Push-Location $repo
try {
    & $PythonExecutable src/mcp/features/assets/generation/document_generation_sources.py --check
    if ($LASTEXITCODE -ne 0) { throw "Source documentation check failed." }
    Build-BridgeRuntime -Repo $repo -DotNet $DotnetExecutable -Python $PythonExecutable -BuildOutput $bin -Staging $stage -RhinoSystem $RhinoSystem
    & $PythonExecutable -B src/rhp/tools/release_version.py --yak-manifest (Join-Path $stage 'manifest.yml')
    if ($LASTEXITCODE -ne 0) { throw 'Yak manifest generation failed.' }
    Copy-Item -LiteralPath (Join-Path $repo "src/mcp/features/assets/guides/rhino-archive-quickstart.md") -Destination (Join-Path $stage "GETTING-STARTED.md")
    Push-Location $stage
    try {
        & $YakExecutable build --platform win
        if ($LASTEXITCODE -ne 0) { throw "Yak build failed." }
    } finally { Pop-Location }
    $packages = @(Get-ChildItem -LiteralPath $stage -Filter *.yak)
    if ($packages.Count -ne 1 -or $packages[0].Name -notlike "*-$rhinoTag-win.yak") { throw "Expected one Windows Yak package matching the referenced Rhino SDK ($rhinoTag)." }
    & $PythonExecutable src/rhp/tools/verify_yak.py $packages[0].FullName --rhino-sdk-version "$($rhinoVersion.Major).$($rhinoVersion.Minor)"
    if ($LASTEXITCODE -ne 0) { throw "Yak contents verification failed." }
    $output = if ([IO.Path]::IsPathRooted($OutputDirectory)) { $OutputDirectory } else { Join-Path $repo $OutputDirectory }
    New-Item -ItemType Directory -Path $output -Force | Out-Null
    Copy-Item -LiteralPath $packages[0].FullName -Destination $output
    Write-Host "Built and verified: $(Join-Path $output $packages[0].Name)"
    Write-Host "Unpublished staging folder: $stage"
} finally { Pop-Location }
