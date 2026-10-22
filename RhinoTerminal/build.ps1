# Build only; no Rhino, Codex, package registration, or global PATH changes.
[CmdletBinding()]
param([string]$OutputDirectory = 'plugin')
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$output=if([IO.Path]::IsPathRooted($OutputDirectory)) {
    [IO.Path]::GetFullPath($OutputDirectory)
} else {
    [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
}
$data=Join-Path $root 'data'
New-Item -ItemType Directory -Path $data -Force | Out-Null
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
$web=Join-Path $root 'src\web'
New-Item -ItemType Directory -Path $web -Force | Out-Null
$vendor=Join-Path $root 'licenses'
New-Item -ItemType Directory -Path $vendor -Force | Out-Null
foreach($p in @(@{name='xterm';version='5.5.0';files=@{'lib/xterm.js'='xterm.js';'css/xterm.css'='xterm.css'}},
                @{name='addon-fit';version='0.10.0';files=@{'lib/addon-fit.js'='addon-fit.js'}})) {
    if(Test-Path -LiteralPath (Join-Path $web ($p.name+'.js'))) {continue}
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
& $sdk build (Join-Path $root 'src\RhinoTerminal.csproj') -c Release -o $output --nologo -p:RestoreLockedMode=true -p:UseSharedCompilation=false -nodeReuse:false
if($LASTEXITCODE){throw 'Plugin build failed.'}
$noticeOutput=Join-Path $output 'licenses'
New-Item -ItemType Directory -Path $noticeOutput -Force | Out-Null
Get-ChildItem -LiteralPath $vendor -File | Copy-Item -Destination $noticeOutput -Force
Write-Host ("Build complete: "+$output+". Nothing was registered or loaded into Rhino.")
