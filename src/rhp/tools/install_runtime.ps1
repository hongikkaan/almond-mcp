# Register fixed runtime paths and migrate Rhino's lazy-load command cache.
# Run again after public Rhino command changes; ordinary code-only pulls keep the paths.
[CmdletBinding()]
param([switch]$VerifyOnly)
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$entries=@(
    @{Name='RhinoAlmondBridge';Guid='c337dbb8-394a-4593-9c2b-a3d7cfc91893';Mode=1;
      Commands=@{};Retired=@('AlmondMCPStart','AlmondMCPStop','AlmondMCPStatus')},
    @{Name='AlmondCOS';Guid='39eb74f6-8283-4e43-bf26-f0106d891b75';Mode=2;
      Commands=@{almondconnect='2;almondconnect';almonddisconnect='2;almonddisconnect'};
      Retired=@('AlmondCOS','AlmondCOSDisconnect')}
)
function Get-CommandRegistrationChanges($entry) {
    $current=if(Test-Path -LiteralPath $entry.CommandKey) {
        Get-ItemProperty -LiteralPath $entry.CommandKey
    } else { [pscustomobject]@{} }
    foreach($name in $entry.Commands.Keys) {
        $property=$current.PSObject.Properties[$name]
        if($null -eq $property -or $property.Value -cne $entry.Commands[$name]) {
            [pscustomobject]@{Action='Set';Name=$name;Value=$entry.Commands[$name]}
        }
    }
    foreach($name in $entry.Retired) {
        if($null -ne $current.PSObject.Properties[$name]) {
            [pscustomobject]@{Action='Remove';Name=$name}
        }
    }
}
foreach($entry in $entries) {
    $entry.File=Join-Path $repo ('src\rhp\'+$entry.Name+'\plugin-runtime\'+$entry.Name+'.rhp')
    if(-not (Test-Path -LiteralPath $entry.File -PathType Leaf)) { throw ('Committed runtime missing: '+$entry.File) }
    if([Reflection.AssemblyName]::GetAssemblyName($entry.File).Name -cne $entry.Name) { throw 'Unexpected runtime assembly.' }
    $entry.Root='HKCU:\Software\McNeel\Rhinoceros\8.0\Plug-ins\'+$entry.Guid
    $entry.Key=$entry.Root+'\PlugIn'
    $entry.CommandKey=$entry.Root+'\CommandList'
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
        $changes=@(Get-CommandRegistrationChanges $entry)
        if($changes.Count) {
            New-Item -Path $entry.CommandKey -Force | Out-Null
            foreach($change in $changes) {
                if($change.Action -eq 'Set') {
                    New-ItemProperty -LiteralPath $entry.CommandKey -Name $change.Name -Value $change.Value -PropertyType String -Force | Out-Null
                } else {
                    Remove-ItemProperty -LiteralPath $entry.CommandKey -Name $change.Name
                }
            }
        }
    }
    Write-Output ('Previous registration backed up: '+$backup)
}
foreach($entry in $entries) {
    if((Get-ItemProperty -LiteralPath $entry.Key -Name FileName).FileName -ine $entry.File) { throw 'Runtime registration differs.' }
    $changes=@(Get-CommandRegistrationChanges $entry)
    if($changes.Count) {
        throw ('Runtime command registration differs: '+$entry.Name+' ('+(($changes | ForEach-Object Name) -join ', ')+'). Close Rhino normally and run install_runtime.ps1 without -VerifyOnly.')
    }
    Write-Output ($entry.Name+': '+$entry.File)
}
Write-Output 'Runtime paths and command cache verified. Start Rhino to load the committed runtime; no build is run at startup.'
