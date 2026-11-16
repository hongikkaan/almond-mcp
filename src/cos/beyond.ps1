# Start the registered direct Codex connection with required user-role guidance.
# Registration, other MCP entries and the user's Codex settings remain owned by Codex.
[CmdletBinding()]
param(
    [string]$WorkDir = (Get-Location).Path,
    [string]$Prompt,
    [switch]$Resume,
    [string]$ResumeSessionId,
    [switch]$ResumeLast,
    [switch]$Exec,
    [switch]$CheckOnly,
    [switch]$Development,
    [string]$CodexPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($Exec -and ($Resume -or $PSBoundParameters.ContainsKey('Prompt'))) {
    throw 'With -Exec, provide the task on stdin and do not use -Resume or -Prompt.'
}
if (($ResumeSessionId -or $ResumeLast) -and -not $Resume) { throw 'ResumeSessionId/ResumeLast requires -Resume.' }
if ($ResumeSessionId -and $ResumeLast) { throw 'Choose a saved session ID or ResumeLast.' }
if ($ResumeSessionId -and $ResumeSessionId -notmatch '^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$') {
    throw 'ResumeSessionId must be a session UUID.'
}

$runtime = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../mcp/runtime'))
$pythonRelative = if ($Development) { '../../data/development/.venv/Scripts/python.exe' } else { '../engine/.venv/Scripts/python.exe' }
$python = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot $pythonRelative))
$hostEntry = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'codex_host.py'))
$guidanceLauncher = Join-Path $runtime 'user_guidance.py'
foreach ($required in @($python, $hostEntry, $guidanceLauncher)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing runtime file: $required. Set up this checkout first." }
}
if (-not $CodexPath -or $CodexPath -ieq 'auto' -or -not (Test-Path -LiteralPath $CodexPath -PathType Leaf)) {
    . (Join-Path $runtime 'codex_path.ps1')
    $CodexPath = Resolve-AlmondCodex -PreferredPath $CodexPath
}
if (-not (Test-Path -LiteralPath $CodexPath -PathType Leaf)) { throw "Codex executable missing: $CodexPath" }

Push-Location -LiteralPath $WorkDir
$previousInput = [Console]::InputEncoding
$previousOutput = [Console]::OutputEncoding
$previousPipe = $OutputEncoding
try {
    [Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    $OutputEncoding = [Text.UTF8Encoding]::new($false)
    $rosterRaw = & $CodexPath mcp list --json
    if ($LASTEXITCODE -ne 0) { throw 'Codex MCP configuration lookup failed. No work session was started.' }
    try { $roster = ($rosterRaw -join "`n") | ConvertFrom-Json }
    catch { throw 'Unexpected Codex MCP configuration output. No work session was started.' }
    $matches = @($roster | Where-Object { $_.name -eq 'rhino' -and $_.enabled -ne $false })
    if ($matches.Count -ne 1) {
        throw 'Register and enable this installation with src/cos/client_config.py before using beyond.ps1. No settings were changed.'
    }
    $entry = $matches[0]
    if ($entry.transport.type -ne 'stdio' -or
        -not [string]::Equals([IO.Path]::GetFullPath([string]$entry.transport.command), $python, [StringComparison]::OrdinalIgnoreCase) -or
        @($entry.transport.args | Where-Object { [string]::Equals([string]$_, $hostEntry, [StringComparison]::OrdinalIgnoreCase) }).Count -ne 1) {
        throw 'The registered rhino MCP belongs to another entry or installation. Preserve it and review client_config.py setup. No settings were changed.'
    }
    if ($CheckOnly) {
        [pscustomobject]@{name='rhino'; enabled=$true} | ConvertTo-Json -Compress
        return
    }

    $arguments = @('--no-daemon')
    if ($Exec) { $arguments = @('exec', '--json', '--ephemeral', '-') }
    elseif ($Resume) {
        $arguments += @('resume', '--cd', [IO.Path]::GetFullPath($WorkDir))
        if ($ResumeSessionId) { $arguments += @($ResumeSessionId) }
        elseif ($ResumeLast) { $arguments += @('--last') }
    }
    $request = @{
        codex = $CodexPath
        arguments = @($arguments)
        cwd = [IO.Path]::GetFullPath($WorkDir)
        prompt = $(if ($PSBoundParameters.ContainsKey('Prompt')) { $Prompt } else { $null })
        stdin_prompt = [bool]$Exec
        powershell = [Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    }
    if ($Resume -and -not $ResumeSessionId -and -not $ResumeLast) {
        $request.prompt_index = [Array]::IndexOf($arguments, 'resume')
    }
    $requestFile = [IO.Path]::GetTempFileName()
    try {
        [IO.File]::WriteAllText($requestFile, ($request | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
        & $python -B -X utf8 -u $guidanceLauncher --request $requestFile
        $code = $LASTEXITCODE
    } finally {
        Remove-Item -LiteralPath $requestFile -Force
    }
    if ($code -ne 0) { throw "Codex exited with code $code." }
} finally {
    [Console]::InputEncoding = $previousInput
    [Console]::OutputEncoding = $previousOutput
    $OutputEncoding = $previousPipe
    Pop-Location
}
