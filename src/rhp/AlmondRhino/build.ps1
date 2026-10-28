# Compatibility entry point. COS owns both its host and Rhino plugin sources.
& (Join-Path $PSScriptRoot '../../cos/build.ps1') @args
