# Fresh isolated build. Does not install or publish anything.
[CmdletBinding()]
param(
    [string]$PythonExecutable = "python",
    [string]$YakExecutable = "C:\Program Files\Rhino 8\System\Yak.exe",
    [string]$DotnetExecutable = "dotnet",
    [string]$RhinoSystem = "C:\Program Files\Rhino 8\System",
    [string]$OutputDirectory = "dist/yak"
)
$ErrorActionPreference = "Stop"
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$rhinoVersion = [Reflection.AssemblyName]::GetAssemblyName((Join-Path $RhinoSystem "RhinoCommon.dll")).Version
if ($rhinoVersion.Major -ne 8) { throw "Expected the installed Rhino 8 SDK." }
$rhinoTag = "rh8_$($rhinoVersion.Minor)"
$stageRoot = Join-Path ([IO.Path]::GetTempPath()) ("almond-yak-" + [guid]::NewGuid().ToString("N"))
$stage = Join-Path $stageRoot "package"
$bin = Join-Path $stageRoot "build"
New-Item -ItemType Directory -Path $stage -Force | Out-Null
if (-not (Test-Path -LiteralPath $YakExecutable)) { throw "Yak executable not found: $YakExecutable" }
Push-Location $repo
try {
    & $PythonExecutable src/mcp/tools/document_generation_sources.py --check
    if ($LASTEXITCODE -ne 0) { throw "Source documentation check failed." }
    & $DotnetExecutable build src/rhp/RhinoAlmondBridge/RhinoAlmondBridge.csproj -c Release -o $bin -p:RestoreLockedMode=true "-p:RhinoSystem=$RhinoSystem"
    if ($LASTEXITCODE -ne 0) { throw "Bridge build failed." }
    Copy-Item -LiteralPath (Join-Path $bin "RhinoAlmondBridge.dll") -Destination (Join-Path $stage "RhinoAlmondBridge.rhp")
    Get-ChildItem -LiteralPath $bin -Filter *.dll | Where-Object Name -ne "RhinoAlmondBridge.dll" | ForEach-Object {
        if ($_.Name -match '^(RhinoCommon|Rhino\.UI|Eto|Grasshopper|GH_IO|Karamba|Kangaroo)') { throw "Forbidden runtime dependency: $($_.Name)" }
        Copy-Item -LiteralPath $_.FullName -Destination $stage
    }
    foreach ($file in @("RhinoAlmondBridge.deps.json", "RhinoAlmondBridge.runtimeconfig.json")) {
        Copy-Item -LiteralPath (Join-Path $bin $file) -Destination $stage
    }
    Copy-Item -LiteralPath (Join-Path $repo "src/rhp/RhinoTerminal/licenses") -Destination (Join-Path $stage "licenses") -Recurse
    & $PythonExecutable src/rhp/tools/build_archive_bundle.py (Join-Path $stage "archive")
    if ($LASTEXITCODE -ne 0) { throw "Archive bundle build failed." }
    Copy-Item -LiteralPath (Join-Path $repo "src/rhp/RhinoAlmondBridge/yak/manifest.yml") -Destination $stage
    foreach ($file in @("LICENSE", "THIRD-PARTY-NOTICES.md")) { Copy-Item -LiteralPath (Join-Path $repo $file) -Destination $stage }
    Copy-Item -LiteralPath (Join-Path $repo "docs/assets/rhino-archive-quickstart.md") -Destination (Join-Path $stage "GETTING-STARTED.md")
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
