# One-time registration of the committed runtime. Subsequent pulls update these same files.
[CmdletBinding()]
param([switch]$VerifyOnly)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$entries=@(
    @{Name='RhinoAlmondBridge';Guid='c337dbb8-394a-4593-9c2b-a3d7cfc91893';Mode=1},
    @{Name='AlmondCOS';Guid='39eb74f6-8283-4e43-bf26-f0106d891b75';Mode=2}
)
foreach($entry in $entries) {
    $entry.File=Join-Path $repo ('src\rhp\'+$entry.Name+'\plugin-runtime\'+$entry.Name+'.rhp')
    if(-not (Test-Path -LiteralPath $entry.File -PathType Leaf)) { throw ('Committed runtime missing: '+$entry.File) }
    if([Reflection.AssemblyName]::GetAssemblyName($entry.File).Name -cne $entry.Name) { throw 'Unexpected runtime assembly.' }
    $entry.Root='HKCU:\Software\McNeel\Rhinoceros\8.0\Plug-ins\'+$entry.Guid
    $entry.Key=$entry.Root+'\PlugIn'
}
$bridgeEngine=Join-Path (Split-Path $entries[0].File -Parent) 'Almond.Engine.dll'
$cosEngine=Join-Path (Split-Path $entries[1].File -Parent) 'Almond.Engine.dll'
if((Get-FileHash -LiteralPath $bridgeEngine).Hash -cne (Get-FileHash -LiteralPath $cosEngine).Hash) {
    throw 'Bridge and COS Engine binaries differ. Pull a complete runtime bundle.'
}
if(-not $VerifyOnly) {
    $backup=Join-Path $repo ('data\runtime-install\'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff'))
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    foreach($entry in $entries) {
        if(Test-Path -LiteralPath $entry.Root) {
            & reg.exe export ('HKCU\Software\McNeel\Rhinoceros\8.0\Plug-ins\'+$entry.Guid) (Join-Path $backup ($entry.Name+'.reg'))
            if($LASTEXITCODE) { throw 'Registration backup failed.' }
        }
    }
    foreach($entry in $entries) {
        New-Item -Path $entry.Key -Force | Out-Null
        Set-ItemProperty -LiteralPath $entry.Root -Name Name -Value $entry.Name
        New-ItemProperty -LiteralPath $entry.Root -Name LoadMode -PropertyType DWord -Value $entry.Mode -Force | Out-Null
        Set-ItemProperty -LiteralPath $entry.Key -Name FileName -Value $entry.File
    }
    Write-Output ('Previous registration backed up: '+$backup)
}
foreach($entry in $entries) {
    if((Get-ItemProperty -LiteralPath $entry.Key -Name FileName).FileName -ine $entry.File) { throw 'Runtime registration differs.' }
    Write-Output ($entry.Name+': '+$entry.File)
}
Write-Output 'Registration ready. Rhino loads the committed runtime; no build is run at startup.'
