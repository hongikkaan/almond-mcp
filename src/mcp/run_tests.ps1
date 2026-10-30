[CmdletBinding()]
param([string[]]$TestArgs = @(), [switch]$Development, [string]$DotNet = '')
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'use_offline_environment.ps1') -Development:$Development -DotNet $DotNet -RequireDotNet
$environmentPath = if ($Development) { '../../data/development/.venv/Scripts/python.exe' } else { '../engine/.venv/Scripts/python.exe' }
$python = Join-Path $PSScriptRoot $environmentPath
# Keep native receipt paths below MAX_PATH without reusing retained failure files.
do {
    $pytestTemporary = Join-Path $env:TEMP ('p' + [guid]::NewGuid().ToString('N').Substring(0, 8))
} while (Test-Path -LiteralPath $pytestTemporary)
& $python -B -X utf8 -m pytest -c (Join-Path $PSScriptRoot 'pytest.ini') (Join-Path $PSScriptRoot 'tests') --basetemp $pytestTemporary @TestArgs
if ($LASTEXITCODE) { throw 'MCP tests failed.' }
