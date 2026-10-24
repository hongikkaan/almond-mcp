# Compatibility entry point for the original installation command.
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot '../mcp/rebuild_environment.ps1') @args
& (Join-Path $PSScriptRoot '../cos/configure.ps1')
