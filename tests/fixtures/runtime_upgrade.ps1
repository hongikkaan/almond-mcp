# Apply the real registration transaction to disposable registry values.
param([Parameter(Mandatory)][string]$Scratch, [switch]$FailOnSecondPlugin)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../../src/rhp/tools/runtime_registration.ps1')
$entries = @(Get-RuntimeRegistration $Scratch)
$bridge, $rhino = $entries
$original = @{ Kind = 'ExpandString'; Value = '%RHINO_BASE%\previous.rhp' }
$unrelated = @{ Kind = 'DWord'; Value = 71 }
$initial = @{}
for ($key = $bridge.Key; $key; $key = Split-Path -Path $key -Parent) {
    $initial[$key] = @{}
}
$initial[$bridge.Root].UserSetting = $unrelated
$initial[$bridge.Key].FileName = $original
$initialKeys = @($initial.Keys)
$fixtureStore = @{
    Keys = $initial
    Fail = $FailOnSecondPlugin.IsPresent
}
$registry = {
    param($Operation, $Path, $Name, $Value)
    switch ($Operation) {
        'Exists' { $fixtureStore.Keys.ContainsKey($Path) }
        'Read' { if ($fixtureStore.Keys.ContainsKey($Path)) { $fixtureStore.Keys[$Path][$Name] } }
        'Backup' {
            ConvertTo-Json -InputObject $fixtureStore.Keys[$bridge.Key]['FileName'] | Set-Content -LiteralPath $Name
        }
        'Create' { $fixtureStore.Keys[$Path] = @{} }
        'Set' {
            $fixtureStore.Keys[$Path][$Name] = $Value
            if ($fixtureStore.Fail -and $Path -eq $rhino.Key -and $Name -eq 'FileName') {
                $fixtureStore.Fail = $false
                throw 'Second plug-in write failed after saving.'
            }
        }
        'Remove' { $fixtureStore.Keys[$Path].Remove($Name) }
        'RemoveEmpty' {
            $hasChildren = @($fixtureStore.Keys.Keys | Where-Object { $_.StartsWith($Path + '\') }).Count -gt 0
            if ($fixtureStore.Keys[$Path].Count -eq 0 -and -not $hasChildren) {
                $fixtureStore.Keys.Remove($Path)
            }
        }
        default { throw "Unexpected registry operation: $Operation" }
    }
}

$installError = $null
try { $backup = Install-RuntimeRegistration $entries $Scratch $registry }
catch { $installError = $_ }

if ($fixtureStore.Keys[$bridge.Root].UserSetting.Kind -ne 'DWord' -or $fixtureStore.Keys[$bridge.Root].UserSetting.Value -ne 71) {
    throw 'The installer replaced a user setting.'
}
if ($FailOnSecondPlugin) {
    if (-not $installError -or $installError.Exception.Message -ne 'Second plug-in write failed after saving.') {
        throw "Expected the registry write failure, received $installError."
    }
    $restored = $fixtureStore.Keys[$bridge.Key].FileName
    if ($restored.Kind -ne 'ExpandString' -or $restored.Value -cne $original.Value) {
        throw "The previous plug-in path or type was not restored: $($restored.Kind) $($restored.Value)."
    }
    $leftovers = @(Compare-Object $initialKeys @($fixtureStore.Keys.Keys))
    if ($fixtureStore.Keys[$bridge.Root].Count -ne 1 -or $fixtureStore.Keys[$bridge.Key].Count -ne 1 -or $leftovers) {
        throw "Unexpected registry after rollback: $($fixtureStore.Keys | ConvertTo-Json -Depth 4 -Compress)."
    }
    return
}

if ($installError) { throw $installError }
$saved = Get-Content -LiteralPath (Join-Path $backup 'RhinoAlmondBridge.reg') -Raw | ConvertFrom-Json
if ($saved.Kind -ne 'ExpandString' -or $saved.Value -cne $original.Value) {
    throw 'The installer did not back up the previous path and type.'
}
foreach ($entry in $entries) {
    $expected = Join-Path $Scratch "src/rhp/$($entry.Name)/plugin-runtime/$($entry.Name).rhp"
    if ($fixtureStore.Keys[$entry.Key].FileName.Value -cne $expected -or $fixtureStore.Keys[$entry.Key].FileName.Kind -ne 'String') {
        throw "Unexpected registered path for $($entry.Name)."
    }
}
foreach ($command in 'almondconnect', 'almonddisconnect') {
    if ($fixtureStore.Keys[$rhino.CommandKey][$command].Value -cne "2;$command") {
        throw "Missing lazy-load registration for $command."
    }
}
Assert-RuntimeRegistration $entries $registry
