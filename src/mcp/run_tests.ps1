[CmdletBinding()]
param([string[]]$TestArgs = @(), [switch]$Development)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'use_offline_environment.ps1') -Development:$Development
$environmentPath = if ($Development) { '../../data/development/.venv/Scripts/python.exe' } else { '../engine/.venv/Scripts/python.exe' }
$python = Join-Path $PSScriptRoot $environmentPath
& $python -B -X utf8 -m pytest -c (Join-Path $PSScriptRoot 'pytest.ini') (Join-Path $PSScriptRoot 'tests') @TestArgs
if ($LASTEXITCODE) { throw 'MCP tests failed.' }
