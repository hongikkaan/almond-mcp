# Build only; no Rhino, Codex, package registration, or global PATH changes.
[CmdletBinding()]
param(
    [string]$OutputDirectory = 'RhinoAlmondBridge\plugin-runtime',
    [string]$PythonExecutable = ''
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
. (Join-Path $root 'tools/build_runtime.ps1')
$repo=Split-Path -Parent (Split-Path -Parent $root)
$terminal=Join-Path $root 'RhinoTerminal'
$output=if([IO.Path]::IsPathRooted($OutputDirectory)) {
    [IO.Path]::GetFullPath($OutputDirectory)
} else {
    [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
}
$bridge=Join-Path $root 'RhinoAlmondBridge'
Assert-RuntimeOutputAvailable $output $bridge
if(-not $PythonExecutable) { $PythonExecutable=Join-Path $repo 'src\engine\.venv\Scripts\python.exe' }
if(-not (Get-Command $PythonExecutable -ErrorAction SilentlyContinue)) { throw "Python environment not found: $PythonExecutable" }
$data=Join-Path $terminal 'data'
New-Item -ItemType Directory -Path $data -Force | Out-Null
$buildData=Join-Path $bridge 'data'
$buildOutput=Join-Path $buildData ('build-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $buildOutput -Force | Out-Null
Initialize-RuntimeBuildEnvironment
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
Build-BridgeRuntime -Repo $repo -DotNet $sdk -Python $PythonExecutable -BuildOutput $buildOutput -Staging $buildOutput
Publish-RuntimeBuild $buildOutput $output $bridge $buildData
Write-Host ("Build complete: "+$output+". Nothing was registered or loaded into Rhino.")
