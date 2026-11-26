# Ask the installed Codex CLI how the launcher settings resolve.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Codex)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$launcher = Join-Path $repo 'src/mcp/runtime/codex.ps1'
$checkoutPython = Join-Path $repo 'src/engine/.venv/Scripts/python.exe'
$probeExecutable = (Resolve-Path -LiteralPath $Codex).Path
$probeMcp = 'fixture_' + [guid]::NewGuid().ToString('N')
$probeDirectory = Join-Path $repo ('data/terminal-config-' + [guid]::NewGuid().ToString('N'))
$wrapper = Join-Path $probeDirectory 'resolve_config.ps1'
$probeFeatures = Join-Path $probeDirectory 'features.txt'
$null = New-Item -ItemType Directory -Path $probeDirectory

# Supply the saved-document preflight facts without starting Rhino or a listener.
function Get-NetTCPConnection {
    param($State, $ErrorAction)
    [pscustomobject]@{LocalAddress='127.0.0.1'; LocalPort=5501; OwningProcess=12345}
}
function Get-Process {
    param($Id, $ErrorAction)
    [pscustomobject]@{ProcessName='Rhino'}
}
function Test-Path {
    param($LiteralPath, $PathType)
    if ($LiteralPath -eq $checkoutPython) { return $true }
    Microsoft.PowerShell.Management\Test-Path -LiteralPath $LiteralPath -PathType $PathType
}

try {
    @'
# Only the installed CLI's read-only config commands are admitted.
if ($args.Count -lt 3 -or ($args[-3..-1] -join ' ') -ne 'mcp list --json') {
    throw 'The config probe cannot launch a Codex session.'
}
$fixture = @('-c', "mcp_servers.$probeMcp.command='unused-fixture.exe'",
             '-c', "mcp_servers.$probeMcp.enabled=true",
             '-c', 'features.apps=true', '-c', 'features.plugins=true')
$roster = & $probeExecutable @fixture @args
if ($LASTEXITCODE) { throw 'Installed CLI roster query failed.' }
$overrides = @($args | Select-Object -First ($args.Count - 3))
$features = & $probeExecutable @fixture @overrides features list
if ($LASTEXITCODE) { throw 'Installed CLI feature query failed.' }
$features | Set-Content -LiteralPath $probeFeatures -Encoding UTF8
$roster
'@ | Set-Content -LiteralPath $wrapper -Encoding UTF8

    $parameters = @{
        Port=5501; AlmondVersion='0.7.0rc2'; RhinoPid=12345; WorkDir=$probeDirectory
        SessionPath=(Join-Path $probeDirectory 'ready.json'); SessionToken='fixture-token'; CodexPath=$wrapper
    }
    foreach ($terminal in @($true, $false)) {
        $roster = (& $launcher @parameters -RhinoTerminal:$terminal -CheckOnly 6>$null) -join "`n" |
            ConvertFrom-Json
        $enabled = @($roster | Where-Object enabled)
        $inherited = @($roster | Where-Object name -eq $probeMcp)
        if ($enabled.Count -ne 1 -or $enabled[0].name -ne 'rhino_session' -or
            $inherited.Count -ne 1 -or $inherited[0].enabled) {
            throw 'The resolved roster did not enable only rhino_session and disable the inherited fixture.'
        }
        $features = Get-Content -LiteralPath $probeFeatures -Encoding UTF8
        $state = if ($terminal) { 'false' } else { 'true' }
        foreach ($feature in @('apps','plugins')) {
            if (-not ($features -match "^$feature\s+\S+\s+$state\s*$")) {
                throw "Expected $feature=$state with RhinoTerminal=$terminal."
            }
        }
    }
    Write-Output 'Installed CLI resolved the expected RhinoTerminal and external settings.'
} finally {
    foreach ($path in @($wrapper, $probeFeatures)) {
        if (Test-Path -LiteralPath $path -PathType Leaf) { Remove-Item -LiteralPath $path -Force }
    }
    if (-not (Get-ChildItem -LiteralPath $probeDirectory -Force)) {
        Remove-Item -LiteralPath $probeDirectory
    }
}
