using System.Reflection;
using AlmondRhino;
using Rhino.Commands;
using RhinoAlmondBridge;

int failures = 0;
var tests = new (string Name, Action Run)[] {
    ("startup registers panels and retains handler without an unbound listener", () => {
        var plugin = new RhinoAlmondBridgePlugin();
        plugin.LoadForTest();
        Check(Rhino.UI.Panels.Registered == 3, "The three existing panels must remain registered.");
        Check(typeof(RhinoAlmondBridgePlugin).GetField("_server", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(plugin) != null,
            "The session Engine still needs the existing native handler.");
        Check(BridgeServer.Starts == 0, "Startup opened the legacy unbound listener.");
    }),
    ("connection command catalogue contains only the two requested names", () => {
        var names = Commands().Select(c => c.EnglishName).Order().ToArray();
        Check(names.SequenceEqual(new[] {"almondconnect", "almonddisconnect"}), "Unexpected commands: " + string.Join(", ", names));
    }),
    ("connect is repeatable and only prepares one discovery host", () => {
        var plugin = new RhinoPlugin();
        var command = Commands().Single(c => c.EnglishName == "almondconnect");
        Check(command.RunForTest() == Result.Success, "Connect failed.");
        var host = plugin.Host;
        Check(host != null && command.RunForTest() == Result.Success && ReferenceEquals(host, plugin.Host),
            "Repeated connect replaced the existing host.");
        Check(host.Disconnects == 0, "Connect disconnected a live session.");
    }),
    ("disconnect without a host stays idle and with a host uses its safe cleanup", () => {
        var plugin = new RhinoPlugin();
        var command = Commands().Single(c => c.EnglishName == "almonddisconnect");
        Check(command.RunForTest() == Result.Success && plugin.Host == null, "Idle disconnect started a host.");
        plugin.Host = new RhinoHost();
        Check(command.RunForTest() == Result.Success && plugin.Host.Disconnects == 1,
            "Disconnect bypassed the existing drain and ownership cleanup.");
    })
};
foreach (var (name, run) in tests) {
    try { run(); Console.WriteLine("PASS " + name); }
    catch (Exception ex) { failures++; Console.Error.WriteLine("FAIL " + name + ": " + ex.Message); }
}
if (args.Length == 2) {
    try { RuntimeContract.Verify(args[0], args[1]); Console.WriteLine("PASS shipped RHP command catalogue and initialized handler contract"); }
    catch (Exception ex) { failures++; Console.Error.WriteLine("FAIL shipped runtime: " + ex.Message); }
}
return failures == 0 ? 0 : 1;

static Command[] Commands() => Assembly.GetExecutingAssembly().GetTypes()
    .Where(t => !t.IsAbstract && typeof(Command).IsAssignableFrom(t))
    .Select(t => (Command)Activator.CreateInstance(t)!).ToArray();
static void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
