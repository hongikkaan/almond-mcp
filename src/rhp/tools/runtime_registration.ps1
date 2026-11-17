# Shared registration identities and the installer transaction. Dot-source from both callers.
function Get-RuntimeRegistration([string]$Repo) {
    $base = 'HKCU:\Software\McNeel\Rhinoceros\8.0\Plug-ins'
    $definitions = @(
        @{ Name = 'RhinoAlmondBridge'; Guid = 'c337dbb8-394a-4593-9c2b-a3d7cfc91893'; Mode = 1
           Commands = @{}; Retired = @('AlmondMCPStart', 'AlmondMCPStop', 'AlmondMCPStatus') },
        @{ Name = 'AlmondRhino'; Guid = '39eb74f6-8283-4e43-bf26-f0106d891b75'; Mode = 2
           Commands = @{ almondconnect = '2;almondconnect'; almonddisconnect = '2;almonddisconnect' }
           Retired = @('AlmondCOS', 'AlmondCOSDisconnect') }
    )
    foreach ($entry in $definitions) {
        $entry.File = Join-Path $Repo "src/rhp/$($entry.Name)/plugin-runtime/$($entry.Name).rhp"
        $entry.Root = "$base\$($entry.Guid)"
        $entry.Key = "$($entry.Root)\PlugIn"
        $entry.CommandKey = "$($entry.Root)\CommandList"
        $entry
    }
}

$runtimeRegistry = {
    param($Operation, $Path, $Name, $State)
    switch ($Operation) {
        'Exists' { Test-Path -LiteralPath $Path; break }
        'Read' {
            if (Test-Path -LiteralPath $Path) {
                $key = Get-Item -LiteralPath $Path
                try {
                    if ($Name -in $key.GetValueNames()) {
                        @{ Kind = $key.GetValueKind($Name).ToString()
                           Value = $key.GetValue($Name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) }
                    }
                } finally { $key.Dispose() }
            }
            break
        }
        'Create' { New-Item -Path $Path | Out-Null; break }
        'Set' {
            New-ItemProperty -LiteralPath $Path -Name $Name -Value $State.Value -PropertyType $State.Kind -Force | Out-Null
            break
        }
        'Remove' { Remove-ItemProperty -LiteralPath $Path -Name $Name; break }
        'RemoveEmpty' {
            if (Test-Path -LiteralPath $Path) {
                $key = Get-Item -LiteralPath $Path
                try {
                    if ($key.ValueCount -eq 0 -and $key.SubKeyCount -eq 0) {
                        Remove-Item -LiteralPath $Path
                    }
                } finally { $key.Dispose() }
            }
            break
        }
        'Backup' {
            # reg.exe accepts HKCU\... rather than HKCU:\...
            $null = & reg.exe export ($Path.Replace(':\', '\')) $Name
            if ($LASTEXITCODE -ne 0) { throw "Registration backup failed for $Path." }
            break
        }
        default { throw "Unknown registry operation: $Operation" }
    }
}

function Test-RegistrationValue($Current, $Expected, [switch]$IgnoreCase) {
    if ($null -eq $Current -or $null -eq $Expected) {
        return $null -eq $Current -and $null -eq $Expected
    }
    if ($Current.Kind -cne $Expected.Kind) { return $false }
    if ($IgnoreCase) { return $Current.Value -ieq $Expected.Value }
    $serializer = [System.Management.Automation.PSSerializer]
    return $serializer::Serialize($Current.Value) -ceq $serializer::Serialize($Expected.Value)
}

function Get-RegistrationPlan($Entries, [scriptblock]$Registry) {
    foreach ($entry in $Entries) {
        $values = @(
            @{ Path = $entry.Root; Name = 'Name'; Desired = @{ Kind = 'String'; Value = $entry.Name } },
            @{ Path = $entry.Root; Name = 'LoadMode'; Desired = @{ Kind = 'DWord'; Value = $entry.Mode } },
            @{ Path = $entry.Key; Name = 'FileName'; Desired = @{ Kind = 'String'; Value = $entry.File } }
        )
        $values += foreach ($name in ($entry.Commands.Keys | Sort-Object)) {
            @{ Path = $entry.CommandKey; Name = $name; Desired = @{ Kind = 'String'; Value = $entry.Commands[$name] } }
        }
        $values += foreach ($name in $entry.Retired) {
            @{ Path = $entry.CommandKey; Name = $name; Desired = $null }
        }
        foreach ($value in $values) {
            $value.Original = & $Registry Read $value.Path $value.Name
            if (-not (Test-RegistrationValue $value.Original $value.Desired -IgnoreCase:($value.Name -eq 'FileName'))) {
                $value
            }
        }
    }
}

function Assert-RuntimeRegistration($Entries, [scriptblock]$Registry = $runtimeRegistry) {
    $differences = @(Get-RegistrationPlan $Entries $Registry)
    if ($differences.Count) {
        $details = ($differences | ForEach-Object { "$($_.Path) / $($_.Name)" }) -join ', '
        throw "Runtime registration differs ($details). Close Rhino normally and run install_runtime.ps1."
    }
}

function Set-RegistrationValue([scriptblock]$Registry, $Change, $State) {
    if ($null -eq $State) {
        & $Registry Remove $Change.Path $Change.Name
    } else {
        & $Registry Set $Change.Path $Change.Name $State
    }
}

function Install-RuntimeRegistration($Entries, [string]$Repo, [scriptblock]$Registry = $runtimeRegistry) {
    $plan = @(Get-RegistrationPlan $Entries $Registry)
    if ($plan.Count -eq 0) { return }

    $backup = Join-Path $Repo ('data/runtime-install/' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    foreach ($entry in $Entries) {
        if (& $Registry Exists $entry.Root) {
            & $Registry Backup $entry.Root (Join-Path $backup ($entry.Name + '.reg'))
        }
    }

    $created = [Collections.Generic.List[string]]::new()
    $applied = [Collections.Generic.List[hashtable]]::new()
    try {
        foreach ($change in $plan) {
            $missing = [Collections.Generic.List[string]]::new()
            $path = $change.Path
            while (-not (& $Registry Exists $path)) {
                $parent = Split-Path -Path $path -Parent
                if (-not $parent -or $path -eq $parent) { throw "Registry root unavailable: $path." }
                $missing.Add($path)
                $path = $parent
            }
            for ($i = $missing.Count - 1; $i -ge 0; $i--) {
                $created.Add($missing[$i])
                & $Registry Create $missing[$i]
            }
            $current = & $Registry Read $change.Path $change.Name
            if (-not (Test-RegistrationValue $current $change.Original)) {
                throw "Registration changed during installation: $($change.Path) / $($change.Name)."
            }
            $applied.Add($change)
            Set-RegistrationValue $Registry $change $change.Desired
        }
        Assert-RuntimeRegistration $Entries $Registry
    } catch {
        $failure = $_
        $rollbackErrors = @(
            for ($i = $applied.Count - 1; $i -ge 0; $i--) {
                $change = $applied[$i]
                try {
                    $current = & $Registry Read $change.Path $change.Name
                    if (Test-RegistrationValue $current $change.Original) { continue }
                    if (-not (Test-RegistrationValue $current $change.Desired)) {
                        throw "Registration changed during rollback: $($change.Path) / $($change.Name)."
                    }
                    Set-RegistrationValue $Registry $change $change.Original
                    if (-not (Test-RegistrationValue (& $Registry Read $change.Path $change.Name) $change.Original)) {
                        throw "Unable to restore $($change.Path) / $($change.Name)."
                    }
                } catch { $_.Exception.Message }
            }
            for ($i = $created.Count - 1; $i -ge 0; $i--) {
                try { & $Registry RemoveEmpty $created[$i] }
                catch { $_.Exception.Message }
            }
        )
        if ($rollbackErrors.Count) {
            throw "Registration failed: $($failure.Exception.Message) Rollback: $($rollbackErrors -join ' ') Backup: $backup"
        }
        throw
    }
    return $backup
}
