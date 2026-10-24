[CmdletBinding()]
param([string[]]$TestArgs = @())
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'use_offline_environment.ps1')
$python = Join-Path $PSScriptRoot '../engine/.venv/Scripts/python.exe'
& $python -B -X utf8 -m pytest -c (Join-Path $PSScriptRoot 'pytest.ini') (Join-Path $PSScriptRoot 'tests') @TestArgs
if ($LASTEXITCODE) { throw 'MCP tests failed.' }
