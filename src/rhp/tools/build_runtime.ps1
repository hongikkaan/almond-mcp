# Shared staging for the two runtime builds and the Bridge Yak package.
function Initialize-RuntimeBuildEnvironment {
    $env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
    $env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
    $env:DOTNET_ADD_GLOBAL_TOOLS_TO_PATH = 'false'
    $env:DOTNET_GENERATE_ASPNET_CERTIFICATE = 'false'
    $env:DOTNET_NOLOGO = '1'
}

function Assert-RuntimeOutputAvailable([string]$OutputDirectory, [string]$InstallDirectory) {
    if ([IO.Path]::GetDirectoryName($OutputDirectory) -ine [IO.Path]::GetFullPath($InstallDirectory) -or
        [IO.Path]::GetFileName($OutputDirectory) -notlike 'plugin-*') {
        throw "Output must be a plugin-* directory directly under $InstallDirectory."
    }
    if (Test-Path -LiteralPath $OutputDirectory) {
        Get-ChildItem -LiteralPath $OutputDirectory -File |
            Where-Object { $_.Extension -in '.dll', '.rhp' } |
            ForEach-Object {
                try { [IO.File]::Open($_.FullName, 'Open', 'ReadWrite', 'None').Dispose() }
                catch { throw "Output is in use; close its Rhino normally before building: $($_.FullName)" }
            }
    }
}

function Publish-RuntimeBuild([string]$Staging, [string]$OutputDirectory, [string]$InstallDirectory, [string]$Data) {
    Assert-RuntimeOutputAvailable $OutputDirectory $InstallDirectory
    $previous = Join-Path $Data ('previous-build-' + [guid]::NewGuid().ToString('N'))
    $dataRoot = [IO.Path]::GetFullPath($Data).TrimEnd('\', '/')
    foreach ($path in $Staging, $previous) {
        if ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($path)) -ine $dataRoot) {
            throw "Build staging must stay directly under $dataRoot."
        }
    }
    if (-not (Test-Path -LiteralPath $Staging -PathType Container)) { throw "Build staging is missing: $Staging" }
    if (Test-Path -LiteralPath $OutputDirectory) { Move-Item -LiteralPath $OutputDirectory -Destination $previous }
    try { Move-Item -LiteralPath $Staging -Destination $OutputDirectory }
    catch {
        if (Test-Path -LiteralPath $previous) { Move-Item -LiteralPath $previous -Destination $OutputDirectory }
        throw
    }
    if (Test-Path -LiteralPath $previous) { Remove-Item -LiteralPath $previous -Recurse -Force }
}

function Build-BridgeRuntime {
    param(
        [string]$Repo,
        [string]$DotNet,
        [string]$Python,
        [string]$BuildOutput,
        [string]$Staging,
        [string]$RhinoSystem = ''
    )
    $project = Join-Path $Repo 'src/rhp/RhinoAlmondBridge/RhinoAlmondBridge.csproj'
    $options = @()
    if ($RhinoSystem) { $options += "-p:RhinoSystem=$RhinoSystem" }
    & $DotNet build $project -c Release -o $BuildOutput --nologo -p:RestoreLockedMode=true -p:UseSharedCompilation=false -nodeReuse:false @options
    if ($LASTEXITCODE -ne 0) { throw 'Bridge build failed.' }

    New-Item -ItemType Directory -Path $Staging -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $BuildOutput 'RhinoAlmondBridge.dll') -Destination (Join-Path $Staging 'RhinoAlmondBridge.rhp')
    if ($Staging -ne $BuildOutput) {
        # Yak includes only runtime dependencies, excludes the source DLL/PDBs,
        # and does not redistribute Rhino's SDK assemblies.
        Get-ChildItem -LiteralPath $BuildOutput -File -Filter *.dll | Where-Object Name -ne 'RhinoAlmondBridge.dll' | ForEach-Object {
            if ($_.Name -match '^(RhinoCommon|Rhino\.UI|Eto|Grasshopper|GH_IO|Karamba|Kangaroo)') {
                throw "Forbidden runtime dependency: $($_.Name)"
            }
            Copy-Item -LiteralPath $_.FullName -Destination $Staging
        }
        foreach ($name in 'RhinoAlmondBridge.deps.json', 'RhinoAlmondBridge.runtimeconfig.json') {
            Copy-Item -LiteralPath (Join-Path $BuildOutput $name) -Destination $Staging
        }
    }
    & $Python (Join-Path $Repo 'src/rhp/tools/build_archive_bundle.py') (Join-Path $Staging 'archive')
    if ($LASTEXITCODE -ne 0) { throw 'Archive bundle build failed.' }
    Copy-Item -LiteralPath (Join-Path $Repo 'src/rhp/RhinoTerminal/licenses') -Destination $Staging -Recurse
    foreach ($name in 'LICENSE', 'THIRD-PARTY-NOTICES.md') {
        Copy-Item -LiteralPath (Join-Path $Repo $name) -Destination $Staging
    }
}
