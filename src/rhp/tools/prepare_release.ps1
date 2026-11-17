# Build-only release pipeline; no upload, install into Rhino, or live MCP changes.
[CmdletBinding()]
param(
    [string]$YakExecutable = "C:\Program Files\Rhino 8\System\Yak.exe",
    [string]$DotNet = ''
)
$ErrorActionPreference = "Stop"
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$scratch = Join-Path $repo ("data/t/r" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $scratch -Force | Out-Null
$previousEnvironment = $env:UV_PROJECT_ENVIRONMENT
$previousLinkMode = $env:UV_LINK_MODE
$previousTemporary = $env:TEMP
$previousTmp = $env:TMP
$env:UV_PROJECT_ENVIRONMENT = Join-Path $scratch "build-env"
$env:UV_LINK_MODE = "copy"
$env:TEMP = $scratch
$env:TMP = $scratch
Push-Location $repo
try {
    & uv sync --locked
    if ($LASTEXITCODE -ne 0) { throw "Dependency sync failed." }
    $python = Join-Path $env:UV_PROJECT_ENVIRONMENT "Scripts/python.exe"
    $version = & $python -c 'from almond_mcp import __version__; print(__version__)'
    if ($LASTEXITCODE -ne 0) { throw "Version read failed." }
    $output = Join-Path $repo "dist/release-$version"
    if ((Test-Path -LiteralPath $output) -and @(Get-ChildItem -LiteralPath $output -Force).Count -gt 0) {
        throw "Release output must be empty; preserve or move the previous artifacts before retrying: $output"
    }
    New-Item -ItemType Directory -Force -Path $output | Out-Null
    # Run the normal developer suite in its own shell so its isolated paths
    # and fixture environment cannot leak into packaging or the caller.
    $shell = (Get-Process -Id $PID).Path
    $sdkArg = if ($DotNet) { @('-DotNet', $DotNet) } else { @() }
    & $shell -NoProfile -NonInteractive -File (Join-Path $repo 'tests/run_tests.ps1') -PythonExecutable $python -ScratchDirectory $scratch -ReleaseReportDirectory $output @sdkArg
    if ($LASTEXITCODE -ne 0) { throw "Release checks failed." }
    & $python src/mcp/features/assets/generation/document_generation_sources.py --check
    if ($LASTEXITCODE -ne 0) { throw "Source check failed." }
    & uv build --out-dir $output
    if ($LASTEXITCODE -ne 0) { throw "Python build failed." }
    $wheel = @(Get-ChildItem -LiteralPath $output -Filter *.whl)
    if ($wheel.Count -ne 1) { throw "Expected one wheel in release directory." }
    & $python src/mcp/release_validation/verify_release.py $wheel[0].FullName
    if ($LASTEXITCODE -ne 0) { throw "Python package verification failed." }
    $install = Join-Path $scratch "install-env"
    & uv venv $install
    if ($LASTEXITCODE -ne 0) { throw "Clean environment creation failed." }
    $installedPython = Join-Path $install "Scripts/python.exe"
    & uv pip install --python $installedPython $wheel[0].FullName
    if ($LASTEXITCODE -ne 0) { throw "Clean wheel install failed." }
    Push-Location $scratch
    try {
        & $installedPython (Join-Path $repo "src/mcp/release_validation/verify_object_archive_install.py") (Join-Path $output "clean-install.json")
        if ($LASTEXITCODE -ne 0) { throw "Installed package smoke test failed." }
    } finally { Pop-Location }
    $yakOutput = Join-Path $scratch "yak"
    $yakBuild = @{ PythonExecutable = $python; YakExecutable = $YakExecutable; OutputDirectory = $yakOutput }
    if ($DotNet) { $yakBuild.DotnetExecutable = $DotNet }
    & (Join-Path $repo "src/rhp/tools/build_yak.ps1") @yakBuild
    $bridgeVersion = & $python -B src/rhp/tools/release_version.py
    if ($LASTEXITCODE -ne 0) { throw "Bridge version read failed." }
    $yakPackages = @(Get-ChildItem -LiteralPath $yakOutput -Filter *.yak)
    if ($yakPackages.Count -ne 1) { throw "Expected one freshly verified Yak package." }
    $yakName = $yakPackages[0].Name
    Copy-Item -LiteralPath $yakPackages[0].FullName -Destination $output
    & $python src/rhp/tools/verify_yak.py (Join-Path $output $yakName) --report (Join-Path $output "yak-verification.json")
    if ($LASTEXITCODE -ne 0) { throw "Final Yak check failed." }
    Copy-Item -LiteralPath (Join-Path $repo "src/mcp/features/assets/guides/rhino-archive-quickstart.md") -Destination $output
    $zip = Join-Path $output "almondbridge-$bridgeVersion-food4rhino.zip"
    Compress-Archive -LiteralPath @((Join-Path $output $yakName), (Join-Path $output "rhino-archive-quickstart.md")) -DestinationPath $zip -Force
    $checksums = Get-ChildItem -LiteralPath $output -File | Where-Object { $_.Name -ne "SHA256SUMS.txt" -and $_.Name -notlike ".*" } | Sort-Object Name | ForEach-Object {
        "{0}  {1}" -f (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(), $_.Name
    }
    $checksums | Set-Content -LiteralPath (Join-Path $output "SHA256SUMS.txt") -Encoding ascii
    Write-Host "Prepared release artifacts: $output"
    Write-Host "Pending: Rhino in-process smoke test and explicit publication. Nothing has been uploaded."
} finally {
    Pop-Location
    $env:UV_PROJECT_ENVIRONMENT = $previousEnvironment
    $env:UV_LINK_MODE = $previousLinkMode
    $env:TEMP = $previousTemporary
    $env:TMP = $previousTmp
}
