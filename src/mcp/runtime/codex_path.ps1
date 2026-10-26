# Resolve an installed Codex CLI without persisting update-specific hash paths.
# Version probes start no agent, MCP service, installer or updater.
function Get-AlmondCodexVersion([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or
        -not [IO.Path]::IsPathRooted($Path) -or
        [IO.Path]::GetExtension($Path) -ine '.exe' -or
        -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    $process = $null
    try {
        $info = New-Object System.Diagnostics.ProcessStartInfo
        $info.FileName = $Path
        $info.Arguments = '--version'
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        $process = [System.Diagnostics.Process]::Start($info)
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $null = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(5000)) {
            $process.Kill() # Only this version-probe child.
            return $null
        }
        if ($process.ExitCode -ne 0) { return $null }
        $text = $stdout.Result.Trim()
        if ($text -notmatch '^codex-cli\s+(\d+\.\d+\.\d+)([^\r\n]*)$') { return $null }
        [pscustomobject]@{
            Path = [IO.Path]::GetFullPath($Path)
            Version = $text
            CoreVersion = [version]$Matches[1]
            Stable = [string]::IsNullOrWhiteSpace($Matches[2])
        }
    } catch {
        return $null
    } finally {
        if ($null -ne $process) { $process.Dispose() }
    }
}

function Resolve-AlmondCodex([string]$PreferredPath = 'auto') {
    # A valid explicit setting wins. A stale/misspelled setting falls back to discovery.
    if ($PreferredPath -and $PreferredPath -ine 'auto') {
        $preferred = Get-AlmondCodexVersion ([Environment]::ExpandEnvironmentVariables($PreferredPath))
        if ($null -ne $preferred) { return $preferred.Path }
    }
    $candidates = @()
    if ($env:CODEX_CLI_PATH) { $candidates += $env:CODEX_CLI_PATH }
    if ($env:LOCALAPPDATA) {
        $bin = Join-Path $env:LOCALAPPDATA 'OpenAI\Codex\bin'
        if (Test-Path -LiteralPath $bin -PathType Container) {
            $candidates += @(Get-ChildItem -LiteralPath $bin -Directory |
                Where-Object { $_.Name -match '^[0-9a-f]{16,64}$' } |
                Sort-Object LastWriteTime -Descending |
                ForEach-Object { Join-Path $_.FullName 'codex.exe' })
        }
        $candidates += Join-Path $bin 'codex.exe'
        $candidates += Join-Path $env:LOCALAPPDATA 'Programs\OpenAI\Codex\bin\codex.exe'
    }
    $candidates += @(Get-Command codex -CommandType Application -All -ErrorAction SilentlyContinue |
        ForEach-Object { $_.Source })
    $available = @(foreach ($candidate in ($candidates | Select-Object -Unique)) {
        $probe = Get-AlmondCodexVersion $candidate
        if ($null -ne $probe) { $probe }
    })
    if ($available.Count -eq 0) {
        throw 'No runnable Codex CLI was found in the installed locations. Open the Codex app once, then run almond or Almond Start again. No settings or software were installed or updated.'
    }
    # Prefer a newer installed CLI, not an older PATH shim. Equal-core stable builds win.
    $selected = $available | Sort-Object CoreVersion, Stable -Descending | Select-Object -First 1
    return $selected.Path
}
