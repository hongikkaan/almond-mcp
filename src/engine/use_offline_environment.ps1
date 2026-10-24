# Compatibility entry point; environment changes remain process-local.
& (Join-Path $PSScriptRoot '../mcp/use_offline_environment.ps1') @args
