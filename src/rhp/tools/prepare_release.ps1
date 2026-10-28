# Build-only release pipeline; no upload, install into Rhino, or live MCP changes.
[CmdletBinding()]
param([string]$YakExecutable = "C:\Program Files\Rhino 8\System\Yak.exe")
$ErrorActionPreference = "Stop"
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$scratch = Join-Path ([IO.Path]::GetTempPath()) ("almond-release-" + [guid]::NewGuid().ToString("N"))
$previousEnvironment = $env:UV_PROJECT_ENVIRONMENT
$previousLinkMode = $env:UV_LINK_MODE
$previousHost = $env:ALMOND_ARCHIVE_TEST_HOST
$env:UV_PROJECT_ENVIRONMENT = Join-Path $scratch "build-env"
$env:UV_LINK_MODE = "copy"
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
    & dotnet build src/rhp/RhinoAlmondBridge/tests/archive_host/ArchiveHost.csproj -c Release -o (Join-Path $scratch "host")
    if ($LASTEXITCODE -ne 0) { throw "Archive host build failed." }
    $env:ALMOND_ARCHIVE_TEST_HOST = Join-Path $scratch "host/ArchiveHost.exe"
    & $python -m pytest -c src/mcp/pytest.ini src/mcp/tests -q --junitxml (Join-Path $output "mcp-tests.xml")
    if ($LASTEXITCODE -ne 0) { throw "MCP module tests failed." }
    & $python -m pytest -q --junitxml (Join-Path $output "tests.xml")
    if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
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
    & (Join-Path $repo "src/rhp/tools/build_yak.ps1") -PythonExecutable $python -YakExecutable $YakExecutable -OutputDirectory $yakOutput
    [xml]$project = Get-Content -LiteralPath (Join-Path $repo "src/rhp/RhinoAlmondBridge/RhinoAlmondBridge.csproj")
    $bridgeVersion = $project.Project.PropertyGroup.Version
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
    $env:ALMOND_ARCHIVE_TEST_HOST = $previousHost
}
