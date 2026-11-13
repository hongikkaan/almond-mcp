# Git paths are resolved from metadata, independent of the worktree's location.
function global:Invoke-AutoVenvGit([string]$Directory, [string]$Arguments) {
    $command = Get-Command git.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $git = if ($command) { $command.Source } elseif ($env:ProgramFiles) {
        Join-Path $env:ProgramFiles 'Git/cmd/git.exe'
    }
    if (-not $git -or -not (Test-Path -LiteralPath $git -PathType Leaf)) { return $null }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo.FileName = $git
    $process.StartInfo.WorkingDirectory = $Directory
    $process.StartInfo.Arguments = $Arguments
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.CreateNoWindow = $true
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    $process.StartInfo.StandardOutputEncoding = [Text.UTF8Encoding]::new()
    try {
        [void]$process.Start()
        $output = $process.StandardOutput.ReadToEnd().TrimEnd("`r", "`n")
        [void]$process.StandardError.ReadToEnd()
        $process.WaitForExit()
        if ($process.ExitCode -eq 0) { return $output }
    } finally { $process.Dispose() }
    return $null
}

function global:Get-AutoVenvRepository([string]$Directory) {
    $worktree = Invoke-AutoVenvGit $Directory 'rev-parse --show-toplevel'
    if (-not $worktree) { return $null }
    $common = Invoke-AutoVenvGit $Directory 'rev-parse --path-format=absolute --git-common-dir'
    if (-not $common) { return $null }
    $common = [IO.Path]::GetFullPath($common)
    # This explicitly reads the main checkout's config.worktree when enabled.
    $root = Invoke-AutoVenvGit $common '--git-dir=. config --path --get core.worktree'
    if ($root) {
        if (-not [IO.Path]::IsPathRooted($root)) { $root = Join-Path $common $root }
    } elseif ((Split-Path $common -Leaf) -ieq '.git') {
        $root = Split-Path $common -Parent
    } else {
        # A separate Git directory without core.worktree has no reverse main-path link.
        return $null
    }
    $root = [IO.Path]::GetFullPath($root)
    if (-not (Test-Path -LiteralPath $root -PathType Container)) { return $null }
    $verifiedRoot = Invoke-AutoVenvGit $root 'rev-parse --show-toplevel'
    $verifiedCommon = Invoke-AutoVenvGit $root 'rev-parse --path-format=absolute --git-common-dir'
    if (-not $verifiedRoot -or -not $verifiedCommon -or
        [IO.Path]::GetFullPath($verifiedRoot) -ine $root -or
        [IO.Path]::GetFullPath($verifiedCommon) -ine $common) { return $null }
    return [PSCustomObject]@{ Root=$root; WorktreeRoot=[IO.Path]::GetFullPath($worktree) }
}

function global:Get-AutoVenvSelection([string]$Directory) {
    $repository = Get-AutoVenvRepository $Directory
    if (-not $repository) { return $null }
    foreach ($relative in '.venv', 'venv', 'data/development/.venv', 'src/engine/.venv') {
        $candidate = Join-Path $repository.Root $relative
        $python = Join-Path $candidate 'Scripts/python.exe'
        if ((Test-Path -LiteralPath (Join-Path $candidate 'pyvenv.cfg') -PathType Leaf) -and
            (Test-Path -LiteralPath $python -PathType Leaf)) {
            return [PSCustomObject]@{ Root=$repository.Root; WorktreeRoot=$repository.WorktreeRoot; Environment=$candidate; Python=$python }
        }
    }
    return [PSCustomObject]@{ Root=$repository.Root; WorktreeRoot=$repository.WorktreeRoot; Environment=$null; Python=$null }
}
