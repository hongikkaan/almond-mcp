# Generate this checkout's COS contract/config; does not register the CoS app.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$python = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../engine/.venv/Scripts/python.exe'))
if (-not (Test-Path -LiteralPath $python)) { throw 'Run src/mcp/rebuild_environment.ps1 first.' }
& $python -B (Join-Path $PSScriptRoot 'build_catalog.py')
if ($LASTEXITCODE) { throw 'COS catalog generation failed.' }
$config = @{
    name = 'Almond COS'
    source = @{kind='command'; command=$python; args=@('-B','-u',(Join-Path $PSScriptRoot 'cos_host.py'))}
    longestCallSeconds = 600
}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'cos-plugin.json'),
    ($config | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
Write-Output 'COS catalog and cos-plugin.json generated. CoS app registration was not changed.'
