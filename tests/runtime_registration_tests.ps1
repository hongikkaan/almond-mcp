# Run the real installer against a fake registry; no Rhino/user registry writes.
$ErrorActionPreference='Stop'
$testRepo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$global:RuntimeRegistrationFixture=@{Registry=@{};Exports=0;CommandWrites=0}
$global:RuntimeRegistrationFixture.Exports=0
$global:RuntimeRegistrationFixture.CommandWrites=0
$script:FailureCount=0
$bridgeRoot='HKCU:\Software\McNeel\Rhinoceros\8.0\Plug-ins\c337dbb8-394a-4593-9c2b-a3d7cfc91893'
$connectionRoot='HKCU:\Software\McNeel\Rhinoceros\8.0\Plug-ins\39eb74f6-8283-4e43-bf26-f0106d891b75'
function Initialize-Fixture {
    $global:RuntimeRegistrationFixture.Registry=@{
        $bridgeRoot=@{Name='RhinoAlmondBridge';LoadMode=1}
        ($bridgeRoot+'\PlugIn')=@{FileName=(Join-Path $testRepo 'src/rhp/RhinoAlmondBridge/plugin-runtime/RhinoAlmondBridge.rhp');UnrelatedSetting='preserve'}
        ($bridgeRoot+'\CommandList')=@{Almond='2;Almond';AlmondMCPStart='2;AlmondMCPStart';AlmondMCPStop='2;AlmondMCPStop';AlmondMCPStatus='2;AlmondMCPStatus'}
        $connectionRoot=@{Name='AlmondCOS';LoadMode=2}
        ($connectionRoot+'\PlugIn')=@{FileName=(Join-Path $testRepo 'src/rhp/AlmondCOS/plugin-runtime/AlmondCOS.rhp')}
        ($connectionRoot+'\CommandList')=@{AlmondCOS='2;AlmondCOS';AlmondCOSDisconnect='2;AlmondCOSDisconnect'}
    }
    $global:RuntimeRegistrationFixture.Exports=0
    $global:RuntimeRegistrationFixture.CommandWrites=0
}
function Test-Path {
    param([string]$LiteralPath,[string]$Path,[string]$PathType)
    $target=if($LiteralPath){$LiteralPath}else{$Path}
    if($target -like 'HKCU:*'){return $global:RuntimeRegistrationFixture.Registry.ContainsKey($target)}
    if($PathType){return Microsoft.PowerShell.Management\Test-Path -LiteralPath $target -PathType $PathType}
    Microsoft.PowerShell.Management\Test-Path -LiteralPath $target
}
function Get-ItemProperty {
    param([string]$LiteralPath,[string]$Name)
    if(-not $global:RuntimeRegistrationFixture.Registry.ContainsKey($LiteralPath)){throw 'Fixture registry key missing'}
    [pscustomobject]$global:RuntimeRegistrationFixture.Registry[$LiteralPath]
}
function New-Item {
    param([string]$Path,[string]$ItemType,[switch]$Force)
    if($Path -like 'HKCU:*'){
        # Registry-provider New-Item -Force overwrites an existing key with an
        # empty key (unlike the filesystem's directory behavior).
        if($global:RuntimeRegistrationFixture.Registry.ContainsKey($Path) -and -not $Force){throw 'Registry key already exists'}
        $global:RuntimeRegistrationFixture.Registry[$Path]=@{}
        return
    }
    Microsoft.PowerShell.Management\New-Item -Path $Path -ItemType $ItemType -Force:$Force
}
function Set-ItemProperty {
    param([string]$LiteralPath,[string]$Name,$Value)
    if($LiteralPath -like '*\CommandList'){
        if($global:RuntimeRegistrationFixture.Exports -ne 2){throw 'Command metadata changed before both registration backups'}
        $global:RuntimeRegistrationFixture.CommandWrites++
    }
    $global:RuntimeRegistrationFixture.Registry[$LiteralPath][$Name]=$Value
}
function New-ItemProperty {
    param([string]$LiteralPath,[string]$Name,$Value,[string]$PropertyType,[switch]$Force)
    Set-ItemProperty -LiteralPath $LiteralPath -Name $Name -Value $Value
}
function Remove-ItemProperty {
    param([string]$LiteralPath,[string]$Name)
    if($global:RuntimeRegistrationFixture.Exports -ne 2){throw 'Command metadata removed before backup'}
    if(-not $global:RuntimeRegistrationFixture.Registry[$LiteralPath].ContainsKey($Name)){throw 'Registry property no longer exists'}
    $global:RuntimeRegistrationFixture.CommandWrites++
    $global:RuntimeRegistrationFixture.Registry[$LiteralPath].Remove($Name)
}
function reg.exe { $global:RuntimeRegistrationFixture.Exports++; $global:LASTEXITCODE=0 }
function Check([bool]$condition,[string]$message){if(-not $condition){throw $message}}
function Run-Case([string]$name,[scriptblock]$action){
    Initialize-Fixture
    try{& $action; Write-Output "PASS $name"}
    catch{$script:FailureCount++; Write-Output "FAIL ${name}: $($_.Exception.Message)`n$($_.ScriptStackTrace)"}
}
Run-Case 'VerifyOnly rejects a correct file path with stale command metadata without writes' {
    $rejected=$false
    try{& "$testRepo/src/rhp/tools/install_runtime.ps1" -VerifyOnly | Out-Null}catch{
        if($_.Exception.Message -notlike 'Runtime command registration differs*'){throw}
        $rejected=$true
    }
    Check $rejected 'Installer incorrectly accepted the old command cache'
    Check ($global:RuntimeRegistrationFixture.CommandWrites -eq 0 -and $global:RuntimeRegistrationFixture.Exports -eq 0) 'VerifyOnly mutated registration'
}
Run-Case 'Install refreshes commands, removes old names and preserves panel commands' {
    & "$testRepo/src/rhp/tools/install_runtime.ps1" | Out-Null
    $commands=$global:RuntimeRegistrationFixture.Registry[$connectionRoot+'\CommandList']
    Check ($commands['almondconnect'] -ceq '2;almondconnect') 'New connect command was not registered'
    Check ($commands['almonddisconnect'] -ceq '2;almonddisconnect') 'New disconnect command was not registered'
    Check (-not $commands.ContainsKey('AlmondCOS') -and -not $commands.ContainsKey('AlmondCOSDisconnect')) 'Old connection command aliases remain'
    $commands=$global:RuntimeRegistrationFixture.Registry[$bridgeRoot+'\CommandList']
    Check ($commands.Count -eq 1 -and $commands['Almond'] -ceq '2;Almond') 'Legacy commands remain or an existing panel command changed'
    Check ($global:RuntimeRegistrationFixture.Registry[$bridgeRoot+'\PlugIn']['UnrelatedSetting'] -ceq 'preserve') 'An unrelated plugin setting changed'
    & "$testRepo/src/rhp/tools/install_runtime.ps1" -VerifyOnly | Out-Null
    $writes=$global:RuntimeRegistrationFixture.CommandWrites
    $global:RuntimeRegistrationFixture.Exports=0
    & "$testRepo/src/rhp/tools/install_runtime.ps1" | Out-Null
    Check ($global:RuntimeRegistrationFixture.CommandWrites -eq $writes) 'Repeated installation rewrote command metadata'
}
Run-Case 'First installation publishes discovery names even without an existing command cache' {
    $global:RuntimeRegistrationFixture.Registry.Remove($bridgeRoot+'\CommandList')
    $global:RuntimeRegistrationFixture.Registry.Remove($connectionRoot+'\CommandList')
    & "$testRepo/src/rhp/tools/install_runtime.ps1" | Out-Null
    $commands=$global:RuntimeRegistrationFixture.Registry[$connectionRoot+'\CommandList']
    Check ($commands.Count -eq 2 -and $commands.ContainsKey('almondconnect') -and $commands.ContainsKey('almonddisconnect')) 'First launch cannot discover the connection commands'
    & "$testRepo/src/rhp/tools/install_runtime.ps1" -VerifyOnly | Out-Null
}
if($script:FailureCount){exit 1}
