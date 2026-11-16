# Real PS -> JSON -> Python -> native PS child boundary. Only OS identity
# observations and final work execution are doubled; installed Codex resolves
# the roster/features under a private CODEX_HOME for every case.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Codex)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$python = Join-Path $repo 'data/development/.venv/Scripts/python.exe'
$windowsPowerShell = Join-Path $env:WINDIR 'System32/WindowsPowerShell/v1.0/powershell.exe'
foreach ($required in @($Codex, $python, $windowsPowerShell)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing test executable: $required" }
}
$temporary = Join-Path $repo ('data/terminal-launch-check/' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $temporary
$wrapper = Join-Path $temporary 'inspect_cli.exe'
$callback = Join-Path $temporary 'inspect_cli.ps1'
$harness = Join-Path $temporary 'launch_case.ps1'
$utf8 = [Text.UTF8Encoding]::new($false)

@'
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Text.UTF8Encoding]::new($false)
$case = [IO.File]::ReadAllText($env:ALMOND_LAUNCH_TEST_CASE) | ConvertFrom-Json
$forwarded = [IO.File]::ReadAllText($case.nativeArguments) | ConvertFrom-Json
$configured = @('-c', "mcp_servers.fixture.command='unused-fixture.exe'", '-c', 'mcp_servers.fixture.enabled=true')
if ($case.kind -eq 'beyond') {
    $registeredPython = if ($case.mismatch) { Join-Path $case.repo 'missing-python.exe' } else { $case.python }
    $hostEntry = Join-Path $case.repo 'src/cos/codex_host.py'
    $configured += @('-c', "mcp_servers.rhino.command='$registeredPython'", '-c', "mcp_servers.rhino.args=['-B','$hostEntry']", '-c', 'mcp_servers.rhino.enabled=true')
}
$isRoster = $forwarded.Count -ge 3 -and $forwarded[-3] -eq 'mcp' -and $forwarded[-2] -eq 'list' -and $forwarded[-1] -eq '--json'
if ($isRoster) {
    [IO.File]::AppendAllText($case.trace, "roster`n")
    & $case.codex @configured @forwarded
    exit $LASTEXITCODE
}
$options = @()
for ($i = 0; $i -lt $forwarded.Count; $i++) {
    if ($forwarded[$i] -eq '-c') { $options += @('-c', [string]$forwarded[++$i]) }
}
$features = & $case.codex @configured @options features list
if ($LASTEXITCODE) { throw 'Installed CLI feature resolution failed' }
$payload = @{
    arguments = @($forwarded)
    stdin = $(if ($case.mode -eq 'exec') { [Console]::In.ReadToEnd() } else { $null })
    appsDisabled = [bool]($features -match '^apps\s+\S+\s+false$')
    pluginsDisabled = [bool]($features -match '^plugins\s+\S+\s+false$')
    guidanceFormat = $env:ALMOND_GUIDANCE_FORMAT
}
$json = $payload | ConvertTo-Json -Depth 8 -Compress
[IO.File]::WriteAllText($case.capture, $json, [Text.UTF8Encoding]::new($false))
Write-Output $json
'@ | Set-Content -LiteralPath $callback -Encoding UTF8

# A native proxy matches the real codex.exe boundary. Windows PowerShell -File
# cannot bind a standalone '-' script argument, so fixture argv is handed to
# its PS callback as JSON data; product scripts are not changed for that limit.
$nativeSource = Join-Path $temporary 'inspect_cli.cs'
@'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
class FixtureCodex {
    static int Main(string[] args) {
        Console.InputEncoding = new UTF8Encoding(false);
        Console.OutputEncoding = new UTF8Encoding(false);
        var json = new JavaScriptSerializer();
        var record = json.Deserialize<Dictionary<string, object>>(File.ReadAllText(Environment.GetEnvironmentVariable("ALMOND_LAUNCH_TEST_CASE")));
        File.WriteAllText((string)record["nativeArguments"], json.Serialize(args), new UTF8Encoding(false));
        bool roster = args.Length >= 3 && args[args.Length-3] == "mcp" && args[args.Length-2] == "list" && args[args.Length-1] == "--json";
        bool stdin = !roster && (string)record["mode"] == "exec";
        var info = new ProcessStartInfo((string)record["powershell"]);
        info.Arguments = "-NoProfile -File \"" + (string)record["callback"] + "\"";
        info.UseShellExecute = false;
        info.CreateNoWindow = true;
        info.RedirectStandardInput = stdin;
        info.RedirectStandardOutput = true;
        info.RedirectStandardError = true;
        info.StandardOutputEncoding = new UTF8Encoding(false);
        info.StandardErrorEncoding = new UTF8Encoding(false);
        using (var process = Process.Start(info)) {
            var output = process.StandardOutput.ReadToEndAsync();
            var error = process.StandardError.ReadToEndAsync();
            if (stdin) {
                byte[] input = Encoding.UTF8.GetBytes(Console.In.ReadToEnd());
                process.StandardInput.BaseStream.Write(input, 0, input.Length);
                process.StandardInput.Close();
            }
            process.WaitForExit();
            Console.Out.Write(output.Result);
            Console.Error.Write(error.Result);
            return process.ExitCode;
        }
    }
}
'@ | Set-Content -LiteralPath $nativeSource -Encoding UTF8
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
& $compiler /nologo /reference:System.Web.Extensions.dll /out:$wrapper $nativeSource
if ($LASTEXITCODE -ne 0) { throw 'Could not build the isolated Codex boundary fixture' }

@'
param([Parameter(Mandatory=$true)][string]$Request)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$case = [IO.File]::ReadAllText($Request) | ConvertFrom-Json
$env:ALMOND_LAUNCH_TEST_CASE = $Request
$env:ALMOND_GUIDANCE_FORMAT = $case.format
$env:CODEX_HOME = $case.codexHome
$env:TEMP = $case.temp
$env:TMP = $case.temp
$env:ALMOND_PROJECT_ROOT = 'unchanged-test-parent-root'
$env:PYTHONDONTWRITEBYTECODE = '1'
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Text.UTF8Encoding]::new($false)
function Get-NetTCPConnection {
    param($State, $ErrorAction)
    [pscustomobject]@{LocalAddress='127.0.0.1';LocalPort=5501;OwningProcess=12345}
}
function Get-Process {
    param($Id, $ErrorAction)
    [pscustomobject]@{ProcessName='Rhino'}
}
$parameters = @{WorkDir=$case.workDir; CodexPath=$case.wrapper; Development=$true}
if ($case.kind -eq 'terminal' -or $case.kind -eq 'external') {
    $launcher = Join-Path $case.repo 'src/mcp/runtime/codex.ps1'
    $parameters.Port=5501; $parameters.AlmondVersion='0.7.0rc2'; $parameters.RhinoPid=12345
    $parameters.SessionPath=Join-Path $case.workDir 'ready.json'; $parameters.SessionToken='fixture-token'
    if ($case.kind -eq 'terminal') { $parameters.RhinoTerminal=$true }
} else { $launcher = Join-Path $case.repo 'src/cos/beyond.ps1' }
if ($case.checkOnly) { $parameters.CheckOnly=$true }
switch ($case.mode) {
    'picker' { $parameters.Resume=$true }
    'id' { $parameters.Resume=$true; $parameters.ResumeSessionId='12345678-1234-1234-1234-123456789abc' }
    'last' { $parameters.Resume=$true; $parameters.ResumeLast=$true }
    'exec' { $parameters.Exec=$true }
}
if ($case.hasPrompt) { $parameters.Prompt=[string]$case.prompt }
try {
    $output = & $launcher @parameters 6>$null
    if ($env:ALMOND_PROJECT_ROOT -ne 'unchanged-test-parent-root') { throw 'Project root environment leaked' }
    $output | ForEach-Object { Write-Output $_ }
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
'@ | Set-Content -LiteralPath $harness -Encoding UTF8

function Invoke-Case([string]$Kind, [string]$Mode, [string]$Format='sequential',
    [bool]$HasPrompt=$true, [string]$Prompt='', [bool]$CheckOnly=$false, [bool]$Mismatch=$false) {
    $caseRoot = Join-Path $temporary ([guid]::NewGuid().ToString('N'))
    $null = New-Item -ItemType Directory -Path $caseRoot
    $case = @{
        repo=$repo; python=$python; codex=$Codex; wrapper=$wrapper; callback=$callback; powershell=$windowsPowerShell
        nativeArguments=(Join-Path $caseRoot 'native-arguments.json'); kind=$Kind; mode=$Mode; format=$Format
        hasPrompt=$HasPrompt; prompt=$Prompt; checkOnly=$CheckOnly; mismatch=$Mismatch
        workDir=$caseRoot; codexHome=(Join-Path $caseRoot 'home'); temp=(Join-Path $caseRoot 'temp')
        capture=(Join-Path $caseRoot 'capture.json'); trace=(Join-Path $caseRoot 'trace.txt')
    }
    $null = New-Item -ItemType Directory -Path $case.codexHome, $case.temp
    # Avoid plugin discovery/network work; apps=true checks Terminal's override.
    [IO.File]::WriteAllText((Join-Path $case.codexHome 'config.toml'), "[features]`nplugins=false`napps=true`n", $utf8)
    $request = Join-Path $caseRoot 'case.json'
    [IO.File]::WriteAllText($request, ($case | ConvertTo-Json -Depth 6), $utf8)
    $info = New-Object Diagnostics.ProcessStartInfo
    $info.FileName = $windowsPowerShell
    # Only generated fixture paths cross this boundary, never user task text.
    $info.Arguments = '-NoProfile -File "' + $harness + '" -Request "' + $request + '"'
    $info.UseShellExecute=$false; $info.CreateNoWindow=$true
    $info.RedirectStandardInput=$true; $info.RedirectStandardOutput=$true; $info.RedirectStandardError=$true
    $info.StandardOutputEncoding=$utf8; $info.StandardErrorEncoding=$utf8
    $process = [Diagnostics.Process]::Start($info)
    try {
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if ($Mode -eq 'exec') {
            $inputBytes = $utf8.GetBytes($Prompt)
            $process.StandardInput.BaseStream.Write($inputBytes, 0, $inputBytes.Length)
        }
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(45000)) {
            # Only this fixture's PID and its descendants are terminated.
            & (Join-Path $env:WINDIR 'System32/taskkill.exe') /PID $process.Id /T /F | Out-Null
            throw "Fixture timed out: $Kind/$Mode/$Format"
        }
        $result = @{exitCode=$process.ExitCode; stdout=$stdout.Result; stderr=$stderr.Result; case=$case}
        if (Test-Path -LiteralPath $case.capture) { $result.capture = [IO.File]::ReadAllText($case.capture) | ConvertFrom-Json }
        if (@(Get-ChildItem -LiteralPath $case.temp -File).Count -ne 0) { throw 'Launcher temporary JSON was not cleaned up' }
        if (-not (Test-Path -LiteralPath $case.trace)) { throw "Installed CLI roster was not queried: $($result.stderr)" }
        return $result
    } finally { $process.Dispose() }
}

function Assert-Case($Result, [string]$Task, [bool]$HasPrompt=$true) {
    $case = $Result.case
    if ($Result.exitCode -ne 0) { throw "Launch failed: $($case.kind)/$($case.mode): $($Result.stderr)" }
    if (-not $Result.ContainsKey('capture')) { throw 'Final native child was not invoked' }
    $captured = $Result.capture
    $arguments = @($captured.arguments)
    $marker = "`n`nUser request:`n"
    if ($case.mode -eq 'exec') {
        $composed = $captured.stdin
        if ($arguments[-1] -ne '-' -or $arguments -notcontains '--ephemeral') { throw 'Exec arguments changed' }
    } else {
        if ($arguments -notcontains '--no-daemon') { throw 'Embedded runtime selection lost' }
        if ($case.mode -eq 'picker') {
            $resumeIndex = [Array]::IndexOf($arguments, 'resume')
            if ($resumeIndex -lt 1) { throw 'Picker resume command missing' }
            $composed = [string]$arguments[$resumeIndex-1]
        } else { $composed = [string]$arguments[-1] }
        if ($case.mode -eq 'id' -and $arguments[-2] -ne '12345678-1234-1234-1234-123456789abc') { throw 'Saved session ID changed' }
        if ($case.mode -eq 'last' -and $arguments[-2] -ne '--last') { throw 'Last session selector changed' }
    }
    $split = $composed.IndexOf($marker, [StringComparison]::Ordinal)
    if ($split -lt 0) { throw 'Required guidance/task boundary missing' }
    $expectedTask = if ($HasPrompt) { $Task } else { '필수 지침을 확인하고 사용자의 작업 요청을 기다리세요.' }
    if ($composed.Substring($split+$marker.Length) -cne $expectedTask) { throw 'Original task changed across native boundaries' }
    $guide = $composed.Substring(0, $split)
    foreach ($name in @('BASIC-INSTRUCTIONS.md','design_judgment.md')) {
        $source = [IO.File]::ReadAllText((Join-Path $repo "src/mcp/$name")).Replace("`r`n", "`n")
        if ($case.format -eq 'fields') {
            $fields = $guide | ConvertFrom-Json
            if ($fields.$name -cne $source) { throw "Full document differs: $name" }
        } elseif ([regex]::Matches($guide, [regex]::Escape($source)).Count -ne 1) { throw "Document must occur once per launch: $name" }
    }
    if ($captured.guidanceFormat -ne $case.format) { throw 'Guidance format environment was not preserved' }
    if ($case.kind -eq 'terminal') {
        if (-not $captured.appsDisabled -or -not $captured.pluginsDisabled) { throw 'Terminal Apps/plugins remained enabled' }
        if ($arguments -notcontains 'mcp_servers.fixture.enabled=false') { throw 'Inherited MCP remained enabled' }
        $forwarded = @($arguments | Where-Object { $_ -like 'mcp_servers.rhino_session.env_vars=*' })
        if ($forwarded.Count -ne 1 -or $forwarded[0] -notmatch "'ALMOND_GUIDANCE_FORMAT'") { throw 'Guidance format was not forwarded to MCP' }
    } else {
        if ($arguments -contains 'features.apps=false' -or $arguments -contains 'features.plugins=false') { throw 'Terminal feature policy leaked outside Terminal' }
        if ($captured.appsDisabled) { throw 'Inherited apps setting was overridden outside Terminal' }
    }
    # Actual native stdout is JSON, not an object shared with the caller.
    $wire = $Result.stdout.Trim() | ConvertFrom-Json
    if (@($wire.arguments).Count -ne $arguments.Count) { throw 'Native JSON output differs from capture' }
}

$completed = $false
try {
    $task = "  원래 `"인용`" '작업' `` `$() \\끝\\`r`nUser request:`nBEGIN REQUIRED DOCUMENT x`n  "
    $count = 0
    foreach ($kind in @('terminal','beyond')) {
        foreach ($format in @('sequential','fields')) {
            $modes = @('new','picker','id','exec','noPrompt')
            if ($kind -eq 'beyond') { $modes += 'last' }
            foreach ($mode in $modes) {
                $hasPrompt = $mode -ne 'noPrompt' -and $mode -ne 'exec'
                $result = Invoke-Case $kind $mode $format $hasPrompt $task
                Assert-Case $result $task ($mode -ne 'noPrompt')
                $count++
            }
        }
        $check = Invoke-Case $kind 'new' 'invalid-loader-format' $false '' $true
        if ($check.exitCode -ne 0 -or $check.ContainsKey('capture')) { throw 'CheckOnly loaded guidance or invoked final child' }
        $count++
        $oversize = Invoke-Case $kind 'new' 'sequential' $true ('긴' * 40000)
        if ($oversize.exitCode -eq 0 -or $oversize.ContainsKey('capture') -or $oversize.stderr -notmatch '32767') { throw 'Oversized command was not rejected before final child' }
        $count++
    }
    Assert-Case (Invoke-Case 'external' 'new' 'sequential' $true $task) $task
    $count++
    $mismatch = Invoke-Case 'beyond' 'new' 'sequential' $true $task $false $true
    if ($mismatch.exitCode -eq 0 -or $mismatch.ContainsKey('capture') -or $mismatch.stderr -notmatch 'another entry or installation') { throw 'Mismatched Beyond registration was accepted' }
    $count++
    Write-Output "Installed CLI guided launch checks passed: $count cases; native stdin, both formats, new/resume, CheckOnly, oversize and registration guards."
    $completed = $true
} finally {
    $target = [IO.Path]::GetFullPath($temporary)
    $allowed = [IO.Path]::GetFullPath((Join-Path $repo 'data/terminal-launch-check')) + '\'
    if (-not $target.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe fixture cleanup path' }
    if ($completed) { Remove-Item -LiteralPath $target -Recurse -Force }
    else { Write-Warning "Failed fixture retained for inspection: $target" }
}
