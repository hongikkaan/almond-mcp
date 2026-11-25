using System.IO.Pipes;
using System.Text.Json;
using AlmondRhino;

var released = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
string name = "Almond-test-" + Guid.NewGuid().ToString("N"), token = Guid.NewGuid().ToString("N"), owner = Guid.NewGuid().ToString("N");
using var server = new ControlPipe(name, token, (request, _) => Task.FromResult<object>(new { accepted = true }), session => { released.TrySetResult(session); return Task.CompletedTask; });
using (var client = new NamedPipeClientStream(".", name, PipeDirection.InOut, PipeOptions.Asynchronous))
{
    await client.ConnectAsync(5000);
    client.ReadMode = PipeTransmissionMode.Message;
    async Task<JsonDocument> Send(object request)
    {
        await client.WriteAsync(JsonSerializer.SerializeToUtf8Bytes(request));
        byte[] data = new byte[65536]; int count = 0;
        do { count += await client.ReadAsync(data.AsMemory(count)); } while (!client.IsMessageComplete);
        return JsonDocument.Parse(data.AsMemory(0, count));
    }
    using (var rejected = await Send(new { id = 1, access_token = "wrong", action = "attach", session_token = owner }))
        if (rejected.RootElement.GetProperty("ok").GetBoolean()) throw new Exception("Wrong access token accepted");
    using (var accepted = await Send(new { id = 2, access_token = token, action = "attach", session_token = owner }))
        if (!accepted.RootElement.GetProperty("ok").GetBoolean()) throw new Exception("Valid owner rejected");
    using (var changed = await Send(new { id = 3, access_token = token, action = "attach", session_token = "other" }))
        if (changed.RootElement.GetProperty("ok").GetBoolean()) throw new Exception("Pipe changed owner");
}
if (await released.Task.WaitAsync(TimeSpan.FromSeconds(5)) != owner) throw new Exception("Disconnected owner not released");
server.Dispose();
await server.Completion.WaitAsync(TimeSpan.FromSeconds(5));
Console.WriteLine("PASS: control token, owner isolation and disconnect cleanup");
