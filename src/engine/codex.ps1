# Uses the fixed local Python runtime. No cache or version-folder dependency.
# Run as a script with &, not by dot-sourcing. Never edits Codex config.toml.
# This is a CLI-scoped configuration override, not a security sandbox.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1024, 65535)]
    [int]$Port,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+(\.\d+){1,3}([A-Za-z0-9.+-]*)$')]
    [string]$AlmondVersion,

    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 2147483647)]
    [int]$RhinoPid,

    [string]$StateDb,
    [string]$WorkDir = (Get-Location).Path,
    [string]$Prompt,
    [switch]$CheckOnly,
    [switch]$Exec,
    [switch]$Resume,
    [string]$ResumeSessionId,
    [string]$RhinoStartTicks,
    [string]$CodexPath,
    [Parameter(Mandatory=$true)][string]$SessionPath,
    [Parameter(Mandatory=$true)][string]$SessionToken
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($Port -eq 5000) { throw 'Use an extra port, not the automatic port 5000.' }
if ($Exec -and $Prompt) { throw 'With -Exec, provide the prompt on stdin; do not also use -Prompt.' }
if ($Resume -and ($Exec -or $Prompt)) { throw 'Resume must be an interactive invocation without an initial prompt.' }
if ($ResumeSessionId -and -not $Resume) { throw 'ResumeSessionId requires -Resume.' }
if ($ResumeSessionId -and $ResumeSessionId -notmatch '^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$') {
    throw 'ResumeSessionId must be a session UUID.'
}

# Single-quoted TOML literals avoid embedded double-quote loss in legacy
# Windows PowerShell's native argument passing. Reject unsupported literals.
function ConvertTo-TomlLiteral([string]$Value) {
    if ($Value.Contains("'''") -or $Value.Contains("`r") -or $Value.Contains("`n")) {
        throw 'A launcher path/value contains three consecutive apostrophes or a newline, which is unsupported.'
    }
    if ($Value.Contains("'")) { return "'''" + $Value + "'''" }
    return "'" + $Value + "'"
}

function Get-CodexMcpList([string]$CodexPath, [string[]]$Overrides = @()) {
    $callArgs = @($Overrides) + @('mcp', 'list', '--json')
    $raw = & $CodexPath @callArgs
    if ($LASTEXITCODE -ne 0) { throw 'codex mcp list failed. No interactive Codex session was started.' }
    try { return (($raw -join "`n") | ConvertFrom-Json) }
    catch { throw 'Unexpected output from codex mcp list --json. Check the installed CLI version.' }
}

$launcher = Join-Path $PSScriptRoot 'mcp_server.py'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw "Missing launcher: $launcher" }
if (-not $CodexPath -or $CodexPath -ieq 'auto' -or
    -not (Test-Path -LiteralPath $CodexPath -PathType Leaf)) {
    . (Join-Path $PSScriptRoot 'codex_path.ps1')
    $CodexPath = Resolve-AlmondCodex -PreferredPath $CodexPath
}
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $CodexPath -PathType Leaf)) { throw "Codex executable missing: $CodexPath" }
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) { throw 'The _engine Python runtime is missing.' }

Push-Location -LiteralPath $WorkDir
$previousInput = [Console]::InputEncoding
$previousOutput = [Console]::OutputEncoding
$previousPipe = $OutputEncoding
try {
    [Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    # OS metadata only. This does not initialize Almond or send a Rhino script.
    $listeners = @(Get-NetTCPConnection -State Listen -ErrorAction Stop |
        Where-Object { $_.LocalAddress -eq '127.0.0.1' -and $_.LocalPort -eq $Port })
    if ($listeners.Count -ne 1 -or $listeners[0].OwningProcess -ne $RhinoPid) {
        throw "Port $Port is not uniquely owned by expected Rhino PID $RhinoPid. Run the Rhino script's Status/Inspect actions."
    }
    $rhino = Get-Process -Id $RhinoPid -ErrorAction Stop
    if ($rhino.ProcessName -ne 'Rhino') { throw "PID $RhinoPid is not a Rhino process." }
    if ($RhinoStartTicks -and $rhino.StartTime.ToUniversalTime().Ticks.ToString() -ne $RhinoStartTicks) {
        throw 'Rhino process start time differs from the bound session. PID may have been reused.'
    }

    $serverName = 'almond_parallel_cli'
    $baseServers = @(Get-CodexMcpList -CodexPath $codexPath -Overrides @())
    $overrides = @()
    foreach ($entry in $baseServers) {
        if ($null -eq $entry) { continue }
        $name = [string]$entry.name
        if ($name -eq $serverName) {
            throw "Reserved MCP name $serverName already exists in config. Remove/rename that conflicting definition manually; this launcher edits no config."
        }
        if ($name -notmatch '^[A-Za-z0-9_-]+$') {
            throw "Unsupported MCP name for dotted CLI overrides: $name. No session was started."
        }
        # Explicitly disable configured MCPs for THIS run; never use mcp_servers={}.
        # Normal Codex windows retain their original settings, including rhino-native.
        if ($entry.enabled -eq $false) { continue }
        # Catalog-provided transports disappear when an enabled override shadows them.
        # Retain their executable only in this disabled CLI entry; no config file changes.
        if ($entry.transport.type -eq 'stdio') {
            $overrides += @('-c', "mcp_servers.$name.command=$(ConvertTo-TomlLiteral ([string]$entry.transport.command))")
        } elseif ($entry.transport.type -eq 'streamable_http') {
            $overrides += @('-c', "mcp_servers.$name.url=$(ConvertTo-TomlLiteral ([string]$entry.transport.url))")
        }
        $overrides += @('-c', "mcp_servers.$name.enabled=false")
    }

    $pythonArgs = @('-B', '-X', 'utf8', '-u', $launcher,
        '--port', [string]$Port, '--expected-version', $AlmondVersion,
        '--session', $SessionPath, '--token', $SessionToken)
    if ($StateDb) {
        if (-not [System.IO.Path]::IsPathRooted($StateDb)) {
            throw 'StateDb must be an absolute path so its project identity is unambiguous.'
        }
        $pythonArgs += @('--state-db', $StateDb)
    }
    $arrayToml = '[' + (($pythonArgs | ForEach-Object { ConvertTo-TomlLiteral $_ }) -join ',') + ']'
    $overrides += @('-c', "mcp_servers.$serverName.command=$(ConvertTo-TomlLiteral $pythonPath)")
    $overrides += @('-c', "mcp_servers.$serverName.args=$arrayToml")
    $overrides += @('-c', "mcp_servers.$serverName.cwd=$(ConvertTo-TomlLiteral $WorkDir)")
    $overrides += @('-c', "mcp_servers.$serverName.enabled=true")
    $overrides += @('-c', "mcp_servers.$serverName.required=true")
    $overrides += @('-c', "mcp_servers.$serverName.startup_timeout_sec=120")
    $overrides += @('-c', "mcp_servers.$serverName.env.PYTHONUTF8='1'")
    $overrides += @('-c', "mcp_servers.$serverName.env.PYTHONIOENCODING='utf-8'")
    # Codex filters inherited variables. Keep the native Windows user-data root
    # and optional explicit library overrides; do not manufacture source paths.
    $runtimeEnv = @('TEMP', 'TMP', 'TMPDIR', 'PYTHONDONTWRITEBYTECODE', 'LOCALAPPDATA',
        'RHINO_MCP_LIBRARY_DIR', 'RHINO_MCP_DRAWING_ASSET_DIR', 'RHINO_MCP_DIAGRAM_ASSET_DIR',
        'RHINO_MCP_GENERATED_ASSET_DIR', 'RHINO_MCP_DRAWING_RECIPE_DIR', 'RHINO_MCP_DRAFTING_DIR',
        'RHINO_MCP_CAPSULE_DIR', 'RHINO_MCP_MATERIAL_DIR', 'RHINO_MCP_CONSTRUCTION_DIR', 'RHINO_MCP_HISTORY_DIR')
    $envToml = '[' + (($runtimeEnv | ForEach-Object { ConvertTo-TomlLiteral $_ }) -join ',') + ']'
    $overrides += @('-c', "mcp_servers.$serverName.env_vars=$envToml")

    # Validate merged config rather than assuming inherited MCPs disappeared.
    # This checks the configuration roster, NOT a successful MCP handshake.
    $effective = @(Get-CodexMcpList -CodexPath $codexPath -Overrides $overrides)
    $active = @($effective | Where-Object { $_.enabled -ne $false })
    if ($active.Count -ne 1 -or $active[0].name -ne $serverName) {
        throw 'Merged MCP roster was not Almond-only. Check managed/plugin/project config. No interactive session was started.'
    }
    Write-Host "Almond -> Rhino PID $RhinoPid (port $Port)"

    if ($CheckOnly) {
        $effective | Select-Object name, enabled | ConvertTo-Json -Depth 3
        Write-Host 'CHECK ONLY: OS port/PID and merged CLI config checked. Almond was NOT initialized; package availability was NOT checked.'
    }
    else {
        if ($Exec) {
            $overrides += @('exec', '--json', '--ephemeral', '-')
        } else {
            # Slot-specific -c overrides require a dedicated embedded TUI runtime.
            # Select it explicitly rather than falling back from the shared daemon.
            # This changes runtime selection only, not approval/sandbox policy.
            $overrides = @('--no-daemon') + $overrides
            if ($Resume) {
                # Start directly in the saved thread, with no intermediate new MCP.
                # An old conversation's cwd must not replace this Rhino binding.
                $overrides += @('resume', '--cd', $WorkDir)
                if ($ResumeSessionId) { $overrides += @($ResumeSessionId) }
            }
        }
        if ($Prompt) { $overrides += @($Prompt) }
        & $codexPath @overrides
        $code = $LASTEXITCODE
        # A new CLI invocation has to use this launcher again; ordinary `codex`
        # intentionally has no Almond registration from this script.
        if ($code -ne 0) { throw "Codex exited with code $code." }
    }
}
finally {
    [Console]::InputEncoding = $previousInput
    [Console]::OutputEncoding = $previousOutput
    $OutputEncoding = $previousPipe
    Pop-Location
}
