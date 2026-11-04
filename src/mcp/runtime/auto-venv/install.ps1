[CmdletBinding()]
param([string]$Destination = (Join-Path $env:USERPROFILE '.config/auto-venv'))
$ErrorActionPreference = 'Stop'
function Get-AutoVenvFileHash([string]$Path) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path))) }
    finally { $sha.Dispose() }
}
$target = [IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Path $target -Force | Out-Null
$backup = $null
foreach ($name in 'repository.ps1', 'auto-venv.cmd', 'auto-venv.ps1') {
    $source = Join-Path $PSScriptRoot $name
    $installed = Join-Path $target $name
    if (Test-Path -LiteralPath $installed) {
        if ((Get-AutoVenvFileHash $source) -eq (Get-AutoVenvFileHash $installed)) { continue }
        if (-not $backup) {
            $backup = Join-Path $target ('backups/' + [DateTime]::Now.ToString('yyyyMMdd-HHmmss-ffff'))
            New-Item -ItemType Directory -Path $backup -Force | Out-Null
        }
        Copy-Item -LiteralPath $installed -Destination (Join-Path $backup $name)
    }
    Copy-Item -LiteralPath $source -Destination $installed -Force
    if ((Get-AutoVenvFileHash $source) -ne (Get-AutoVenvFileHash $installed)) {
        throw "Installed file verification failed: $installed"
    }
}
# The existing CMD AutoRun and PowerShell profiles already point here.
# This installer restores files; it does not replace any shell registration.
[PSCustomObject]@{installed_directory=$target;backup_directory=$backup;files=@('repository.ps1','auto-venv.cmd','auto-venv.ps1')}
