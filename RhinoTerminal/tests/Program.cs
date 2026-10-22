using System.Diagnostics;
using System.Text;
using RhinoTerminal;

var root = Path.GetFullPath(args.Single());
if (!Directory.Exists(root)) throw new Exception("Supply the existing workspace data directory.");
var fixture = Path.Combine(root, "terminal-smoke-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(fixture);
static string Q(string s) => "'" + s.Replace("'", "''") + "'";
static async Task WaitFor(Func<bool> predicate, string description)
{
    var limit = Stopwatch.StartNew();
    while (!predicate())
    {
        if (limit.Elapsed > TimeSpan.FromSeconds(15)) throw new Exception("Timeout: " + description);
        await Task.Delay(50);
    }
}
static bool Alive(int pid)
{
    try { using var p = Process.GetProcessById(pid); return !p.HasExited; }
    catch (ArgumentException) { return false; }
}
static async Task Drain(TerminalSession session, StringBuilder output)
{
    await foreach (var value in session.Output.Reader.ReadAllAsync()) output.Append(value);
}
var session = new TerminalSession();
var output = new StringBuilder();
var drain = Drain(session, output);
var childPid = 0;
try
{
    session.Start(fixture, "$u=New-Object System.Text.UTF8Encoding($false); [Console]::OutputEncoding=$u; [Console]::InputEncoding=$u; $OutputEncoding=$u");
    await WaitFor(() => session.Pid > 0, "contained shell");
    var proof = Path.Combine(fixture, "한글 test.txt");
    await session.Write("[IO.File]::WriteAllText(" + Q(proof) + ",'한글 입력 확인',[Text.Encoding]::UTF8)\r");
    await WaitFor(() => File.Exists(proof), "Unicode command round trip");
    if (File.ReadAllText(proof) != "한글 입력 확인") throw new Exception("Unicode input mismatch");
    Console.WriteLine("PASS: real ConPTY + UTF-8 Korean input + Korean/spaced path");
    session.Resize(113, 35);
    var size = Path.Combine(fixture, "size.txt");
    await session.Write("[IO.File]::WriteAllText(" + Q(size) + ", [string]$Host.UI.RawUI.WindowSize.Width)\r");
    await WaitFor(() => File.Exists(size), "resize");
    if (File.ReadAllText(size) != "113") throw new Exception("Resize mismatch: " + File.ReadAllText(size));
    Console.WriteLine("PASS: live terminal resize");
    var pidFile = Path.Combine(fixture, "child.txt");
    await session.Write("$s=New-Object Diagnostics.ProcessStartInfo; $s.FileName=$PSHOME+'\\powershell.exe'; " +
        "$s.Arguments='-NoLogo -NoProfile -Command Start-Sleep -Seconds 90'; $s.UseShellExecute=$false; $s.CreateNoWindow=$true; " +
        "$p=[Diagnostics.Process]::Start($s); [IO.File]::WriteAllText(" + Q(pidFile) + ",[string]$p.Id)\r");
    await WaitFor(() => File.Exists(pidFile) && File.ReadAllText(pidFile).Length > 0, "owned child");
    childPid = int.Parse(File.ReadAllText(pidFile));
    if (!Alive(childPid)) throw new Exception("Child not running");
    session.Stop();
    await session.Completion!.WaitAsync(TimeSpan.FromSeconds(15));
    await WaitFor(() => !Alive(session.Pid) && !Alive(childPid), "shell/child disposal");
    await drain.WaitAsync(TimeSpan.FromSeconds(5));
    Console.WriteLine("PASS: stop removes this shell and its real descendant; test host survives");
}
finally { session.Stop(); }

var normal = new TerminalSession();
var normalOutput = new StringBuilder();
var normalDrain = Drain(normal, normalOutput);
try
{
    normal.Start(fixture, "Write-Output 'normal-start'");
    await WaitFor(() => normal.Pid > 0, "second shell");
    await normal.Write("exit 7\r");
    await normal.Completion!.WaitAsync(TimeSpan.FromSeconds(15));
    await normalDrain.WaitAsync(TimeSpan.FromSeconds(5));
    if (!normalOutput.ToString().Contains("터미널 종료: 7")) throw new Exception("Actual exit code not preserved: " + normalOutput);
    Console.WriteLine("PASS: process exit code and tail output retained");
}
finally { normal.Stop(); }

var early = new TerminalSession();
early.Start(fixture, "Write-Output 'early'");
early.Stop();
await early.Completion!.WaitAsync(TimeSpan.FromSeconds(15));
Console.WriteLine("PASS: stop during startup");
Directory.Delete(fixture, true);
Console.WriteLine("All five live backend checks passed; disposable fixture removed.");
