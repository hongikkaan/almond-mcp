# Runs actual registration planning/verification against a fake registry.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Scratch)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
. (Join-Path $repo 'src/rhp/tools/runtime_registration.ps1')

function Assert-That([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

$entries = @(Get-RuntimeRegistration $Scratch)
$bridge, $rhino = $entries
$registry = {
    param($Operation, $Path, $Name, $State)
    switch ($Operation) {
        'Exists' { $fake.Keys.ContainsKey($Path); break }
        'Read' {
            if ($fake.Keys.ContainsKey($Path)) { $fake.Keys[$Path][$Name] }
            break
        }
        'Backup' {
            if ($fake.FailBackup) { throw 'Injected backup failure.' }
            [IO.File]::WriteAllText($Name, $Path)
            break
        }
        default {
            if (++$fake.Writes -eq $fake.FailWrite) {
                if ($fake.ChangeOtherValue) {
                    $fake.Keys[$bridge.Root]['Name'] = @{ Kind = 'String'; Value = 'A newer registration' }
                }
                if ($fake.SkipWrite) { break }
                if (-not $fake.FailAfterWrite) { throw 'Injected write failure.' }
            }
            switch ($Operation) {
                'Create' { $fake.Keys[$Path] = @{} }
                'Set' { $fake.Keys[$Path][$Name] = $State }
                'Remove' { $fake.Keys[$Path].Remove($Name) }
                'RemoveEmpty' {
                    $child = @($fake.Keys.Keys | Where-Object { $_.StartsWith($Path + '\') })
                    if ($fake.Keys[$Path].Count -eq 0 -and $child.Count -eq 0) {
                        $fake.Keys.Remove($Path)
                    }
                }
                default { throw "Unexpected action: $Operation" }
            }
            if ($fake.Writes -eq $fake.FailWrite) { throw 'Injected write failure.' }
        }
    }
}
function Reset-Fake {
    $fake.Writes = 0
    $fake.FailWrite = -1
    $fake.FailBackup = $false
    $fake.ChangeOtherValue = $false
    $fake.FailAfterWrite = $false
    $fake.SkipWrite = $false
    $fake.Keys = @{
        (Split-Path $bridge.Root -Parent) = @{}
        $bridge.Root = @{
            Name = @{ Kind = 'String'; Value = 'Old Bridge' }
            LoadMode = @{ Kind = 'String'; Value = '2' }
            UserSetting = @{ Kind = 'DWord'; Value = 71 }
        }
        $bridge.Key = @{
            FileName = @{ Kind = 'ExpandString'; Value = '%MY_DEV_DIR%\plugin.rhp' }
        }
        $bridge.CommandKey = @{
            AlmondMCPStart = @{ Kind = 'String'; Value = 'retired' }
            UserCommand = @{ Kind = 'String'; Value = 'keep' }
        }
    }
}
function Get-RegistrationSnapshot {
    $lines = foreach ($path in $fake.Keys.Keys | Sort-Object) {
        $path
        foreach ($name in $fake.Keys[$path].Keys | Sort-Object) {
            $value = $fake.Keys[$path][$name]
            "$name|$($value.Kind)|$($value.Value)"
        }
    }
    $lines -join "`n"
}

$fake = @{}
Reset-Fake
$initial = Get-RegistrationSnapshot
$null = Install-RuntimeRegistration $entries $Scratch $registry
$operationCount = $fake.Writes
Assert-That ($operationCount -ge 10) 'Missing multi-key registration writes.'
Assert-That ($fake.Keys[$bridge.Root].UserSetting.Value -eq 71) 'User setting was overwritten.'
Assert-That ($fake.Keys[$bridge.CommandKey].UserCommand.Value -eq 'keep') 'User command was overwritten.'
Assert-That (-not $fake.Keys[$bridge.CommandKey].ContainsKey('AlmondMCPStart')) 'Retired name persisted.'
Assert-That ($fake.Keys[$rhino.CommandKey].almondconnect.Value -ceq '2;almondconnect') 'New command was not cached.'
$null = Install-RuntimeRegistration $entries $Scratch $registry
Assert-That ($fake.Writes -eq $operationCount) 'An idempotent install changed registration.'
Assert-RuntimeRegistration $entries $registry

$fake.Keys[$bridge.Root]['LoadMode'] = @{ Kind = 'DWord'; Value = 2 }
try {
    Assert-RuntimeRegistration $entries $registry
    throw 'Wrong LoadMode passed verification.'
} catch {
    Assert-That ($_.Exception.Message -match '\bLoadMode\b' -and
        $_.Exception.Message -ne 'Wrong LoadMode passed verification.') $_.Exception.Message
}
Assert-That ($fake.Writes -eq $operationCount) 'Verification wrote to the registry.'

foreach ($failAfterWrite in $false, $true) {
    foreach ($failure in 1..$operationCount) {
        Reset-Fake
        $fake.FailWrite = $failure
        $fake.FailAfterWrite = $failAfterWrite
        try {
            $null = Install-RuntimeRegistration $entries $Scratch $registry
            throw 'Injected failure did not fail the installation.'
        } catch {
            Assert-That ($_.Exception.Message -match 'Injected write failure') $_.Exception.Message
        }
        Assert-That ((Get-RegistrationSnapshot) -ceq $initial) "Registration not restored after step $failure."
    }
}
Reset-Fake
$fake.FailWrite = $operationCount
$fake.ChangeOtherValue = $true
try {
    $null = Install-RuntimeRegistration $entries $Scratch $registry
    throw 'Concurrent change did not fail the installation.'
} catch {
    Assert-That ($_.Exception.Message -match 'changed during rollback') $_.Exception.Message
}
Assert-That ($fake.Keys[$bridge.Root].Name.Value -ceq 'A newer registration') 'Rollback clobbered a concurrent edit.'
Assert-That (-not $fake.Keys.ContainsKey($rhino.Root)) 'Rollback stopped at the first conflict.'

Reset-Fake
$fake.FailWrite = $operationCount
$fake.SkipWrite = $true
try {
    $null = Install-RuntimeRegistration $entries $Scratch $registry
    throw 'Final verification passed after a silently dropped write.'
} catch {
    Assert-That ($_.Exception.Message -match 'Runtime registration differs') $_.Exception.Message
}
Assert-That ((Get-RegistrationSnapshot) -ceq $initial) 'Final verification failure did not restore registration.'

Reset-Fake
$fake.FailBackup = $true
try {
    $null = Install-RuntimeRegistration $entries $Scratch $registry
    throw 'Backup failure did not fail the installation.'
} catch {
    Assert-That ($_.Exception.Message -match 'Injected backup failure') $_.Exception.Message
}
Assert-That ($fake.Writes -eq 0) 'Registration changed without a backup.'

Reset-Fake
$fake.Keys = @{ 'HKCU:\Software' = @{} }
$clean = Get-RegistrationSnapshot
$fake.FailWrite = 7
try {
    $null = Install-RuntimeRegistration $entries $Scratch $registry
    throw 'Fresh registry failed to exercise rollback of missing parents.'
} catch {
    Assert-That ($_.Exception.Message -match 'Injected write failure') $_.Exception.Message
}
Assert-That ((Get-RegistrationSnapshot) -ceq $clean) 'Installer left empty keys after rollback on first install.'
$fake.FailWrite = -1
$null = Install-RuntimeRegistration $entries $Scratch $registry
Assert-RuntimeRegistration $entries $registry
Write-Output "$operationCount injected mutation points checked before and after writing."
