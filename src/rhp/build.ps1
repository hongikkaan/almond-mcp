# Build only; no Rhino, Codex, package registration, or global PATH changes.
[CmdletBinding()]
param(
    [string]$OutputDirectory = 'RhinoAlmondBridge\plugin-runtime',
    [string]$PythonExecutable = ''
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$repo=Split-Path -Parent (Split-Path -Parent $root)
$terminal=Join-Path $root 'RhinoTerminal'
$output=if([IO.Path]::IsPathRooted($OutputDirectory)) {
    [IO.Path]::GetFullPath($OutputDirectory)
} else {
    [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
}
$bridge=Join-Path $root 'RhinoAlmondBridge'
if([IO.Path]::GetDirectoryName($output) -ine [IO.Path]::GetFullPath($bridge) -or
   [IO.Path]::GetFileName($output) -notlike 'plugin-*') {
    throw 'Output must be a plugin-* directory directly under RhinoAlmondBridge so the shared Engine path stays valid.'
}
if(Test-Path -LiteralPath $output) {
    Get-ChildItem -LiteralPath $output -File | Where-Object { $_.Extension -in '.dll','.rhp' } | ForEach-Object {
        $candidate=$_.FullName
        try { $probe=[IO.File]::Open($candidate,'Open','ReadWrite','None'); $probe.Dispose() }
        catch { throw "Output is in use; close its Rhino normally before building: $candidate" }
    }
}
if(-not $PythonExecutable) { $PythonExecutable=Join-Path $repo 'src\engine\.venv\Scripts\python.exe' }
if(-not (Get-Command $PythonExecutable -ErrorAction SilentlyContinue)) { throw "Python environment not found: $PythonExecutable" }
$data=Join-Path $terminal 'data'
New-Item -ItemType Directory -Path $data -Force | Out-Null
$buildOutput=Join-Path $bridge ('data\build-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $buildOutput -Force | Out-Null
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1'
$env:DOTNET_NOLOGO='1'
$sdk=Join-Path $data 'sdk\dotnet.exe'
if(-not (Test-Path -LiteralPath $sdk)) {
    $installed=Get-Command dotnet.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if($installed -and (& $installed.Source --list-sdks)) { $sdk=$installed.Source }
}
if(-not (Test-Path -LiteralPath $sdk)) {
    $release=Invoke-RestMethod 'https://builds.dotnet.microsoft.com/dotnet/release-metadata/8.0/releases.json'
    $version=$release.'latest-sdk'
    $entry=@($release.releases | Where-Object {$_.sdk.version -eq $version})[0].sdk
    $file=@($entry.files | Where-Object {$_.rid -eq 'win-x64' -and $_.name -like '*.zip'})[0]
    $zip=Join-Path $data 'sdk.zip'
    Write-Host "Downloading build-only .NET SDK $version"
    $client=New-Object Net.WebClient
    try {$client.DownloadFile($file.url,$zip)} finally {$client.Dispose()}
    if((Get-FileHash -LiteralPath $zip -Algorithm SHA512).Hash -ine $file.hash) {throw 'SDK SHA512 mismatch.'}
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::ExtractToDirectory($zip,(Join-Path $data 'sdk'))
    Remove-Item -LiteralPath $zip
}
$web=Join-Path $terminal 'src\web'
New-Item -ItemType Directory -Path $web -Force | Out-Null
$vendor=Join-Path $terminal 'licenses'
New-Item -ItemType Directory -Path $vendor -Force | Out-Null
foreach($p in @(@{name='xterm';version='5.5.0';files=@{'lib/xterm.js'='xterm.js';'css/xterm.css'='xterm.css'}},
                @{name='addon-fit';version='0.10.0';files=@{'lib/addon-fit.js'='addon-fit.js'}})) {
    if((Test-Path -LiteralPath (Join-Path $web ($p.name+'.js'))) -and
       (Test-Path -LiteralPath (Join-Path $vendor ($p.name+'-LICENSE.txt')))) {continue}
    $meta=Invoke-RestMethod ("https://registry.npmjs.org/@xterm/"+$p.name+'/'+$p.version)
    $archive=Join-Path $data ($p.name+'.tgz')
    $client=New-Object Net.WebClient
    try {$client.DownloadFile($meta.dist.tarball,$archive)} finally {$client.Dispose()}
    $sha=[Security.Cryptography.SHA512]::Create()
    try {$actual='sha512-'+[Convert]::ToBase64String($sha.ComputeHash([IO.File]::ReadAllBytes($archive)))} finally {$sha.Dispose()}
    if($actual -cne $meta.dist.integrity){throw 'xterm package integrity mismatch.'}
    $unpack=Join-Path $data ($p.name+'-unpack')
    New-Item -ItemType Directory -Path $unpack -Force | Out-Null
    & tar.exe -xzf $archive -C $unpack
    if($LASTEXITCODE){throw 'tar extraction failed.'}
    foreach($source in $p.files.Keys) {Copy-Item -LiteralPath (Join-Path $unpack ('package/'+$source)) -Destination (Join-Path $web $p.files[$source])}
    Copy-Item -LiteralPath (Join-Path $unpack 'package/LICENSE') -Destination (Join-Path $vendor ($p.name+'-LICENSE.txt'))
    Remove-Item -LiteralPath $archive,$unpack -Recurse -Force
}
& $sdk build (Join-Path $bridge 'RhinoAlmondBridge.csproj') -c Release -o $buildOutput --nologo -p:RestoreLockedMode=true -p:UseSharedCompilation=false -nodeReuse:false
if($LASTEXITCODE){throw 'Plugin build failed.'}
Copy-Item -LiteralPath (Join-Path $buildOutput 'RhinoAlmondBridge.dll') -Destination (Join-Path $buildOutput 'RhinoAlmondBridge.rhp') -Force
& $PythonExecutable (Join-Path $repo 'src\rhp\tools\build_archive_bundle.py') (Join-Path $buildOutput 'archive')
if($LASTEXITCODE){throw 'Archive bundle build failed.'}
$noticeOutput=Join-Path $buildOutput 'licenses'
New-Item -ItemType Directory -Path $noticeOutput -Force | Out-Null
Get-ChildItem -LiteralPath $vendor -File | Copy-Item -Destination $noticeOutput -Force
foreach($name in 'LICENSE','THIRD-PARTY-NOTICES.md') {
    Copy-Item -LiteralPath (Join-Path $repo $name) -Destination $buildOutput -Force
}
$previous=Join-Path $bridge ('data\previous-build-'+[guid]::NewGuid().ToString('N'))
if(Test-Path -LiteralPath $output) { Move-Item -LiteralPath $output -Destination $previous }
try { Move-Item -LiteralPath $buildOutput -Destination $output }
catch {
    if(Test-Path -LiteralPath $previous) { Move-Item -LiteralPath $previous -Destination $output }
    throw
}
if(Test-Path -LiteralPath $previous) { Remove-Item -LiteralPath $previous -Recurse -Force }
Write-Host ("Build complete: "+$output+". Nothing was registered or loaded into Rhino.")
