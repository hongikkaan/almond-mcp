using System.Diagnostics;
using System.Text.Json;
using AlmondRhino;

using var process = Process.GetCurrentProcess();
var pipe = $"AlmondRhino-{process.Id}-{Guid.NewGuid():N}";
var access = Guid.NewGuid().ToString("N");
var timeout = TimeSpan.FromSeconds(20);
using var server = new ControlPipe(pipe, access, Respond, Release);

Console.WriteLine(JsonSerializer.Serialize(new
{
    pid = process.Id,
    process_start_ticks = process.StartTime.ToUniversalTime().Ticks.ToString(),
    access_token = access,
    pipe
}));

// EOF lets the test stop the fixture after the pipe has released its owner.
await Console.In.ReadLineAsync().WaitAsync(timeout);
server.Dispose();
await server.Completion.WaitAsync(timeout);

static Task<object> Respond(JsonElement request, CancellationToken _)
{
    var session = request.GetProperty("session_token").GetString();
    return Task.FromResult<object>(new { session });
}

static Task Release(string owner)
{
    Console.WriteLine(owner);
    return Task.CompletedTask;
}
