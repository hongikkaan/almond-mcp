# Dot-source from the current-user profile. Compatible with PowerShell 5.1 and 7.
. (Join-Path $PSScriptRoot 'repository.ps1')
function global:Find-AutoVenv {
    $location = Get-Location
    if ($location.Provider.Name -ne 'FileSystem') { return $null }
    Get-AutoVenvSelection $location.ProviderPath
}
function global:Update-AutoVenv {
    # Respect environments explicitly activated by the user or another launcher.
    if ($env:VIRTUAL_ENV -and $env:VIRTUAL_ENV -ine $env:AUTO_VENV_ACTIVE) { return }
    $selection = $null
    if (-not $env:AUTO_VENV_DISABLE) { $selection = Find-AutoVenv }
    $selected = $null
    $env:AUTO_VENV_WORKTREE_ROOT = $null
    $env:AUTO_VENV_REPO_ROOT = $null
    $env:AUTO_VENV_PYTHON = $null
    if ($selection) {
        $env:AUTO_VENV_WORKTREE_ROOT = $selection.WorktreeRoot
        $env:AUTO_VENV_REPO_ROOT = $selection.Root
        $env:AUTO_VENV_PYTHON = $selection.Python
        $selected = $selection.Environment
    }
    if ([string]$selected -ieq [string]$env:AUTO_VENV_ACTIVE) { return }
    if ($env:AUTO_VENV_ACTIVE) {
        $env:PATH = $env:AUTO_VENV_BASE_PATH
        $env:PYTHONHOME = $env:AUTO_VENV_OLD_PYTHONHOME
        $env:VIRTUAL_ENV = $null
        $env:AUTO_VENV_ACTIVE = $null
        $env:AUTO_VENV_BASE_PATH = $null
        $env:AUTO_VENV_OLD_PYTHONHOME = $null
    }
    if (-not $selected) { return }
    $env:AUTO_VENV_BASE_PATH = $env:PATH
    $env:AUTO_VENV_OLD_PYTHONHOME = $env:PYTHONHOME
    $env:AUTO_VENV_ACTIVE = $selected
    $env:VIRTUAL_ENV = $selected
    $env:PYTHONHOME = $null
    $env:PATH = (Join-Path $selected 'Scripts') + [IO.Path]::PathSeparator + $env:PATH
}

$autoVenvPromptState = Get-Variable -Name AutoVenvPromptInstalled -Scope Global -ErrorAction SilentlyContinue
if (-not $autoVenvPromptState -or -not $autoVenvPromptState.Value) {
    $global:AutoVenvOriginalPrompt = (Get-Item -LiteralPath Function:\prompt).ScriptBlock
    $global:AutoVenvPromptInstalled = $true
    function global:prompt {
        try { Update-AutoVenv } catch { Write-Warning ('auto-venv: ' + $_.Exception.Message) }
        $prefix = ''
        if ($env:AUTO_VENV_ACTIVE -and $env:VIRTUAL_ENV -ieq $env:AUTO_VENV_ACTIVE) {
            $prefix = '(' + (Split-Path $env:AUTO_VENV_ACTIVE -Leaf) + ') '
        }
        $prefix + (& $global:AutoVenvOriginalPrompt)
    }
}
Remove-Variable -Name autoVenvPromptState -ErrorAction SilentlyContinue
Update-AutoVenv
