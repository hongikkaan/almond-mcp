using System.Diagnostics;
using System.Text;
using System.Text.Json;
using AlmondCOS;

// A disposable console process, with no Rhino references, slots, ports or models.
Console.OutputEncoding = new UTF8Encoding(false);
using var process = Process.GetCurrentProcess();
string name = "AlmondCOS-" + process.Id + "-fixture-" + Guid.NewGuid().ToString("N");
string access = Guid.NewGuid().ToString("N");
var released = new List<string>();
string attached = "";
var resume = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
using var pipe = new ControlPipe(name, access, async (request, cancellation) =>
{
    switch (request.GetProperty("action").GetString())
    {
        case "describe": return new { attached, released = released.ToArray() };
        case "echo": return new { text = request.GetProperty("text").GetString() };
        case "large": return new { text = new string('한', 10000) };
        case "attach":
            attached = request.GetProperty("session_token").GetString()!;
            if (request.TryGetProperty("hold", out var hold) && hold.GetBoolean())
            {
                Console.WriteLine("ATTACHED");
                await resume.Task.WaitAsync(cancellation);
            }
            return new { attached = true };
        case "detach":
            if (attached != request.GetProperty("session_token").GetString())
                throw new InvalidOperationException("Fixture owner mismatch");
            attached = "";
            return new { detached = true };
        default: throw new InvalidOperationException("Fixture action mismatch");
    }
}, owner =>
{
    released.Add(owner);
    if (owner == attached) attached = "";
    return Task.CompletedTask;
});
Console.WriteLine(JsonSerializer.Serialize(new {
    host_id = "fixture", pid = process.Id, process_start_ticks = process.StartTime.ToUniversalTime().Ticks.ToString(),
    pipe = name, access_token = access
}));
while (await Console.In.ReadLineAsync() is string line)
{
    if (line == "go") resume.TrySetResult();
    if (line == "stop") break;
}
pipe.Dispose();
await pipe.Completion.WaitAsync(TimeSpan.FromSeconds(3));
