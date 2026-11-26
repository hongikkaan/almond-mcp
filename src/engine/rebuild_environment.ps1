# Compatibility entry point for the original installation command.
[CmdletBinding()]
param([switch]$Development, [switch]$VerifyOnly)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot '../mcp/rebuild_environment.ps1') -Development:$Development -VerifyOnly:$VerifyOnly
