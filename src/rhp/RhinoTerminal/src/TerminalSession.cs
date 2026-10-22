#nullable enable
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading.Channels;
using System.Threading;
using System.Threading.Tasks;
using Porta.Pty;

namespace RhinoTerminal;

internal sealed class TerminalSession
{
    readonly object gate = new();
    readonly CancellationTokenSource cancel = new();
    readonly SemaphoreSlim writer = new(1, 1);
    readonly TaskCompletionSource<int> exited = new(TaskCreationOptions.RunContinuationsAsynchronously);
    IPtyConnection? connection;
    ProcessJob? job;
    bool stopped;
    int columns = 90, rows = 28;
    public int Pid { get; private set; }
    public Task? Completion { get; private set; }
    public Channel<string> Output { get; } = Channel.CreateBounded<string>(128);
    public event Action<string>? Status;

    public void Start(string cwd, string script)
    {
        Completion = Task.Run(() => Run(cwd, script));
    }

    async Task Run(string cwd, string script)
    {
        IPtyConnection? own = null;
        Task? reader = null;
        try
        {
            lock (gate) { if (stopped) return; job = ProcessJob.Create(); }
            var env = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (DictionaryEntry e in Environment.GetEnvironmentVariables())
                if (e.Key is string k && e.Value is string v) env[k] = v;
            // Only the child environment is changed. Rhino's embedded Python can
            // export these variables; they are inappropriate for a normal shell.
            foreach (var name in new[] { "PYTHONHOME", "PYTHONPATH", "PYTHONEXECUTABLE" }) env.Remove(name);
            env["TERM"] = "xterm-256color";
            env["COLORTERM"] = "truecolor";
            env["RHINO_TERMINAL_HOST_PID"] = Environment.ProcessId.ToString();
            var args = new[] { "-NoLogo", "-NoProfile", "-NoExit", "-EncodedCommand",
                Convert.ToBase64String(Encoding.Unicode.GetBytes(script)) };
            var shell = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows),
                "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
            own = await PtyProvider.SpawnAsync(new PtyOptions {
                Name="RhinoTerminal", App=shell, CommandLine=args, Cwd=cwd,
                Cols=columns, Rows=rows, Environment=env
            }, CancellationToken.None).ConfigureAwait(false);

            // The first shell input is gated until containment is established.
            lock (gate)
            {
                if (stopped) return;
                job!.Add(own.Pid);
                connection = own; Pid = own.Pid;
                connection.Resize(columns, rows);
            }
            own.ProcessExited += (_, e) => exited.TrySetResult(e.ExitCode);
            Status?.Invoke($"PowerShell · PID {Pid}");
            reader = Read(own);
            var code = await exited.Task.ConfigureAwait(false);
            // Do not dispose the connection in the exit callback: the reader may
            // still be draining the CLI's actual error output.
            await Task.WhenAny(reader, Task.Delay(1500)).ConfigureAwait(false);
            if (!cancel.IsCancellationRequested)
            {
                await Output.Writer.WriteAsync($"\r\n[터미널 종료: {code}] 새 터미널을 누르면 다시 열립니다.\r\n", cancel.Token);
                Status?.Invoke($"종료 코드 {code}");
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception ex)
        {
            if (!cancel.IsCancellationRequested)
            {
                await Output.Writer.WriteAsync("\r\n[실행 오류] " + ex.Message + "\r\n", cancel.Token);
                Status?.Invoke("실행 오류 — 아래 메시지 확인");
            }
        }
        finally
        {
            lock (gate) { connection = null; job?.Dispose(); job = null; }
            // Keep output draining while ClosePseudoConsole releases its handles.
            try { own?.Kill(); } catch { }
            try { own?.Dispose(); } catch { }
            cancel.Cancel();
            if (reader != null) await Task.WhenAny(reader, Task.Delay(1000)).ConfigureAwait(false);
            Output.Writer.TryComplete();
        }
    }

    async Task Read(IPtyConnection own)
    {
        var bytes = new byte[8192];
        var decoder = Encoding.UTF8.GetDecoder();
        var chars = new char[Encoding.UTF8.GetMaxCharCount(bytes.Length)];
        try
        {
            while (!cancel.IsCancellationRequested)
            {
                int n = await own.ReaderStream.ReadAsync(bytes, 0, bytes.Length, cancel.Token).ConfigureAwait(false);
                if (n == 0) break;
                int count = decoder.GetChars(bytes, 0, n, chars, 0);
                if (count > 0) await Output.Writer.WriteAsync(new string(chars, 0, count), cancel.Token);
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception ex)
        {
            if (!cancel.IsCancellationRequested && !exited.Task.IsCompleted)
                await Output.Writer.WriteAsync("\r\n[출력 오류] " + ex.Message + "\r\n", cancel.Token);
        }
        finally
        {
            // EOF alone must not be reported as successful exit code 0.
            if (!exited.Task.IsCompleted) { await Task.Delay(200); exited.TrySetResult(-1); }
        }
    }

    public async Task Write(string text)
    {
        if (text.Length > 1024 * 1024) return;
        try
        {
            await writer.WaitAsync(cancel.Token).ConfigureAwait(false);
            try
            {
                IPtyConnection? own;
                lock (gate) own = connection;
                if (own == null) return;
                byte[] bytes = Encoding.UTF8.GetBytes(text);
                await own.WriterStream.WriteAsync(bytes, cancel.Token).ConfigureAwait(false);
                await own.WriterStream.FlushAsync(cancel.Token).ConfigureAwait(false);
            }
            finally { writer.Release(); }
        }
        catch (OperationCanceledException) { }
        catch (Exception ex) { Status?.Invoke("입력 중단: " + ex.Message); }
    }

    public void Resize(int cols, int lines)
    {
        lock (gate)
        {
            columns = Math.Clamp(cols, 20, 500); rows = Math.Clamp(lines, 5, 200);
            try { connection?.Resize(columns, rows); } catch { /* Exit/resize race. */ }
        }
    }

    public void Stop()
    {
        lock (gate)
        {
            if (stopped) return;
            stopped = true;
            // Releasing this exact handle synchronously works even at Rhino shutdown.
            job?.Dispose(); job = null;
        }
        cancel.Cancel();
        exited.TrySetResult(-1);
    }
}
