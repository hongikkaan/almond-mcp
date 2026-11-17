[CmdletBinding()]
param(
    [string[]]$TestArgs = @(), [switch]$Development, [string]$DotNet = '',
    [string]$PythonExecutable = '', [string]$ScratchDirectory = ''
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'use_offline_environment.ps1') -Development:$Development -DotNet $DotNet -RequireDotNet -PythonExecutable $PythonExecutable -ScratchDirectory $ScratchDirectory
$python = $env:ALMOND_TEST_PYTHON
# Keep native receipt paths below MAX_PATH without reusing retained failure files.
do {
    $pytestTemporary = Join-Path $env:TEMP ('p' + [guid]::NewGuid().ToString('N').Substring(0, 8))
} while (Test-Path -LiteralPath $pytestTemporary)
& $python -B -X utf8 -m pytest -c (Join-Path $PSScriptRoot 'pytest.ini') (Join-Path $PSScriptRoot 'tests') --basetemp $pytestTemporary @TestArgs
if ($LASTEXITCODE) { throw 'MCP tests failed.' }
