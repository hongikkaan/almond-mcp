# Register fixed runtime paths and migrate Rhino's lazy-load command cache.
# Run again after public Rhino command changes; ordinary code-only pulls keep the paths.
[CmdletBinding()]
param([switch]$VerifyOnly)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
. (Join-Path $PSScriptRoot 'runtime_registration.ps1')
$entries = @(Get-RuntimeRegistration $repo)
$engineHashes = foreach ($entry in $entries) {
    if (-not (Test-Path -LiteralPath $entry.File -PathType Leaf)) { throw "Committed runtime missing: $($entry.File)" }
    if ([Reflection.AssemblyName]::GetAssemblyName($entry.File).Name -cne $entry.Name) { throw 'Unexpected runtime assembly.' }
    (Get-FileHash -LiteralPath (Join-Path (Split-Path $entry.File -Parent) 'Almond.Engine.dll')).Hash
}
if ($engineHashes[0] -cne $engineHashes[1]) {
    throw 'Bridge and AlmondRhino Engine binaries differ. Pull a complete runtime bundle.'
}
if ($VerifyOnly) {
    Assert-RuntimeRegistration $entries
} else {
    $backup = Install-RuntimeRegistration $entries $repo
    if ($backup) { Write-Output "Previous registration backed up: $backup" }
}
foreach ($entry in $entries) { Write-Output "$($entry.Name): $($entry.File)" }
Write-Output 'Runtime paths, load modes and command cache verified. Start Rhino to load the committed runtime; no build is run at startup.'
