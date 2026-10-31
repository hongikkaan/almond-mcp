# Check the real launch script with the installed CLI's config resolver.
# Only OS identity observations and the final interactive invocation are doubled.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Codex)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$launcher = Join-Path $repo 'src/mcp/runtime/codex.ps1'
$expectedPython = Join-Path $repo 'src/engine/.venv/Scripts/python.exe'
$temporary = Join-Path $repo ('data/terminal-launch-check/' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $temporary
$wrapper = Join-Path $temporary 'inspect_cli.ps1'
$originalRoot = $env:ALMOND_PROJECT_ROOT

function Get-NetTCPConnection {
    param($State, $ErrorAction)
    [pscustomobject]@{LocalAddress='127.0.0.1';LocalPort=5501;OwningProcess=12345}
}
function Get-Process {
    param($Id, $ErrorAction)
    [pscustomobject]@{ProcessName='Rhino'}
}
function Test-Path {
    param($LiteralPath, $PathType)
    if ($LiteralPath -eq $expectedPython) { return $true }
    Microsoft.PowerShell.Management\Test-Path -LiteralPath $LiteralPath -PathType $PathType
}

@'
$options = @()
for ($i = 0; $i -lt $args.Count; $i++) {
    if ($args[$i] -eq '-c') { $options += @('-c', [string]$args[++$i]) }
}
# Supply a configured inherited MCP through CLI flags, never config.toml.
$configured = @('-c', "mcp_servers.fixture.command='unused-fixture.exe'", '-c', 'mcp_servers.fixture.enabled=true')
if ($args -contains 'list') {
    & $Codex @configured @args
    if ($LASTEXITCODE) { throw 'Installed CLI config roster query failed' }
} else {
    $features = & $Codex @options features list
    if ($LASTEXITCODE) { throw 'Installed CLI feature resolution failed' }
    [pscustomobject]@{
        arguments=@($args)
        appsDisabled=[bool]($features -match '^apps\s+\S+\s+false$')
        pluginsDisabled=[bool]($features -match '^plugins\s+\S+\s+false$')
    }
}
'@ | Set-Content -LiteralPath $wrapper -Encoding UTF8

$parameters = @{Port=5501;AlmondVersion='0.7.0rc2';RhinoPid=12345;WorkDir=$temporary;
    SessionPath=(Join-Path $temporary 'ready.json');SessionToken='fixture-token';CodexPath=$wrapper}
try {
    foreach ($mode in @('new','resume','exec')) {
        $flags = @{RhinoTerminal=$true}
        if ($mode -eq 'resume') { $flags.Resume=$true }
        if ($mode -eq 'exec') { $flags.Exec=$true }
        $result = & $launcher @parameters @flags
        if (-not $result.appsDisabled -or -not $result.pluginsDisabled) { throw "${mode}: Apps/plugins remained enabled" }
        if ($result.arguments -notcontains 'mcp_servers.fixture.enabled=false') { throw "${mode}: inherited MCP was not disabled" }
        if ($mode -ne 'exec' -and $result.arguments -notcontains '--no-daemon') { throw "${mode}: embedded runtime lost" }
        if ($mode -eq 'resume' -and $result.arguments -notcontains 'resume') { throw 'Resume command lost' }
        if ($mode -eq 'exec' -and $result.arguments -notcontains '--ephemeral') { throw 'Exec isolation lost' }
    }
    $outside = & $launcher @parameters
    if ($outside.arguments -contains 'features.apps=false' -or $outside.arguments -contains 'features.plugins=false') {
        throw 'RhinoTerminal feature policy leaked into the external launcher'
    }
    $roster = (& $launcher @parameters -RhinoTerminal -CheckOnly) -join "`n" | ConvertFrom-Json
    $enabled = @($roster | Where-Object enabled)
    if ($enabled.Count -ne 1 -or $enabled[0].name -ne 'rhino_session') { throw 'CheckOnly roster differs' }
    if ($env:ALMOND_PROJECT_ROOT -ne $originalRoot) { throw 'Project root environment leaked' }
    Write-Output 'Installed CLI launch/config checks passed: new, resume, exec, external scope and CheckOnly.'
} finally {
    $target = [IO.Path]::GetFullPath($temporary)
    $allowed = [IO.Path]::GetFullPath((Join-Path $repo 'data/terminal-launch-check')) + '\'
    if (-not $target.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe cleanup path' }
    Remove-Item -LiteralPath $target -Recurse -Force
}
