[CmdletBinding()]
param([string]$Database, [switch]$Development, [switch]$NoBrowser, [int]$Port = 0, [switch]$PickFile)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
. (Join-Path $PSScriptRoot 'auto-venv/repository.ps1')
$selection = Get-AutoVenvSelection $repo
if (-not $selection) {
    throw 'Cannot resolve the original Git checkout. Check Git and the main repository core.worktree setting.'
}
$pythonRepo = $selection.Root
$python = if ($Development) { Join-Path $pythonRepo 'data/development/.venv/Scripts/python.exe' } else { $selection.Python }
if (-not $python -or -not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python environment missing in original repository: $pythonRepo"
}
Write-Verbose "Original repository: $pythonRepo"
Write-Verbose "Python: $python"
Write-Verbose "Dashboard source: $PSScriptRoot"
if ($PickFile -and -not $Database) {
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.OpenFileDialog
    $picker.Title = 'Almond - Select SQLite DB (read only)'
    $picker.Filter = 'SQLite (*.sqlite3;*.sqlite;*.db)|*.sqlite3;*.sqlite;*.db|All files (*.*)|*.*'
    try {
        if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { return }
        $Database = $picker.FileName
    } finally { $picker.Dispose() }
}
if ($Database) { $Database = (Resolve-Path -LiteralPath $Database).Path }
Push-Location $PSScriptRoot
try {
    $dashboardArgs = @('-B', '-X', 'utf8', '-m', 'dashboard', '--port', "$Port")
    if ($NoBrowser) { $dashboardArgs += '--no-browser' }
    if ($Database) { $dashboardArgs += @('--', $Database) }
    & $python @dashboardArgs
    if ($LASTEXITCODE) { throw 'DB Dashboard stopped with an error.' }
} finally { Pop-Location }
