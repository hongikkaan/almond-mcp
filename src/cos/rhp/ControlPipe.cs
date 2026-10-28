using System.IO.Pipes;
using System.Text;
using System.Text.Json;

namespace AlmondRhino;

// Message-mode framing matches CPython multiprocessing.connection.send_bytes,
// not its pickle send()/recv() APIs. No Rhino or executable code travels here.
internal sealed class ControlPipe : IDisposable
{
    readonly string name, token;
    readonly Func<JsonElement, CancellationToken, Task<object>> handle;
    readonly Func<string, Task> disconnected;
    readonly CancellationTokenSource stop = new();
    NamedPipeServerStream? active;
    internal Task Completion { get; }

    internal ControlPipe(string name, string token,
        Func<JsonElement, CancellationToken, Task<object>> handle,
        Func<string, Task> disconnected)
    {
        this.name = name; this.token = token; this.handle = handle; this.disconnected = disconnected;
        Completion = Task.Run(Listen);
    }

    async Task Listen()
    {
        while (!stop.IsCancellationRequested)
        {
            string owner = "";
            try
            {
                using var pipe = new NamedPipeServerStream(name, PipeDirection.InOut, 1,
                    PipeTransmissionMode.Message, PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly, 65536, 65536);
                active = pipe;
                await pipe.WaitForConnectionAsync(stop.Token).ConfigureAwait(false);
                while (!stop.IsCancellationRequested && pipe.IsConnected)
                {
                    var bytes = new byte[8193];
                    int size = await pipe.ReadAsync(bytes, stop.Token).ConfigureAwait(false);
                    if (size == 0) break;
                    using var deadline = CancellationTokenSource.CreateLinkedTokenSource(stop.Token);
                    deadline.CancelAfter(TimeSpan.FromSeconds(25));
                    while (!pipe.IsMessageComplete)
                    {
                        if (size >= 8192) throw new IOException("Control request too large.");
                        int n = await pipe.ReadAsync(bytes.AsMemory(size), deadline.Token).ConfigureAwait(false);
                        if (n == 0) throw new IOException("Incomplete control message.");
                        size += n;
                    }
                    if (size > 8192) throw new IOException("Control request too large.");
                    long id = 0;
                    object response;
                    try
                    {
                        using var json = JsonDocument.Parse(bytes.AsMemory(0, size));
                        var request = json.RootElement.Clone();
                        id = request.GetProperty("id").GetInt64();
                        if (request.GetProperty("access_token").GetString() != token)
                            throw new InvalidOperationException("Invalid AlmondRhino control token.");
                        // Mark a possible owner before Attach: its reply can be lost.
                        var action = request.GetProperty("action").GetString();
                        if (action == "attach")
                        {
                            var candidate = request.GetProperty("session_token").GetString() ?? "";
                            if (!string.IsNullOrEmpty(owner) && candidate != owner)
                                throw new InvalidOperationException("A control pipe cannot change session owner.");
                            owner = candidate;
                        }
                        var result = await handle(request, deadline.Token).WaitAsync(deadline.Token).ConfigureAwait(false);
                        if (action == "detach") owner = "";
                        response = new { id, ok = true, result };
                    }
                    catch (Exception ex) { response = new { id, ok = false, error = ex.GetBaseException().Message }; }
                    var output = JsonSerializer.SerializeToUtf8Bytes(response);
                    if (output.Length > 65536) throw new IOException("Control response too large.");
                    await pipe.WriteAsync(output, deadline.Token).ConfigureAwait(false);
                }
            }
            catch (Exception ex) when (ex is IOException or OperationCanceledException or ObjectDisposedException) { }
            finally
            {
                active = null;
                if (!string.IsNullOrEmpty(owner))
                {
                    try { await disconnected(owner).ConfigureAwait(false); }
                    catch (Exception) { /* The Rhino owner retains its leases on failure. */ }
                }
            }
        }
    }

    public void Dispose()
    {
        stop.Cancel();
        active?.Dispose();
    }
}
