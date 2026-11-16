# Compatibility entry for the cross-module launcher contract test.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Codex)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot '../../../../tests/integration/test_guided_launch.ps1') -Codex $Codex
