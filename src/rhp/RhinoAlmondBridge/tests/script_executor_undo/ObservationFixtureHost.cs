using System;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
using Rhino.Runtime.InProcess;

// CLI-only headless observations. Never opens a user model or loads a candidate RHP.
internal static class ObservationFixtureHost
{
    [STAThread]
    static int Main(string[] args)
    {
        if (args.Length != 1) throw new ArgumentException("Supply one new report file under an isolated test directory.");
        var report = Path.GetFullPath(args[0]);
        if (File.Exists(report)) throw new ArgumentException("The report must be new.");
        var system = Environment.GetEnvironmentVariable("RHINO_SYSTEM_DIR") ?? @"C:\Program Files\Rhino 8\System";
        AppDomain.CurrentDomain.AssemblyResolve += (sender, request) =>
        {
            var file = Path.Combine(system, new AssemblyName(request.Name).Name + ".dll");
            return File.Exists(file) ? Assembly.LoadFrom(file) : null;
        };
        try
        {
            var result = Run();
            File.WriteAllText(report, result, new System.Text.UTF8Encoding(false));
            Console.WriteLine(result);
            return 0;
        }
        catch (Exception error)
        {
            File.WriteAllText(report, error.ToString(), new System.Text.UTF8Encoding(false));
            Console.Error.WriteLine(error);
            return 1;
        }
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    static string Run()
    {
        using (var core = new RhinoCore(new[] { "/NOSPLASH", "/NOTEMPLATE" }, WindowStyle.NoWindow))
        {
            string report = AlmondScriptUndoTests.ObservationTests.RunAll();
            using (var doc = Rhino.RhinoDoc.CreateHeadless(null))
            {
                var before = RhinoAlmondBridge.EditingContext.Observe(doc);
                if ((string)before["mode"] != "model" || !(bool)before["stable"])
                    throw new InvalidOperationException("Clean CLI model baseline was not stable.");
                // A late, unsupported provider must not borrow a cached inactive baseline.
                System.Reflection.Emit.AssemblyBuilder.DefineDynamicAssembly(
                    new AssemblyName("BlockEditNew, Version=999.0.0.0"), System.Reflection.Emit.AssemblyBuilderAccess.Run);
                var after = RhinoAlmondBridge.EditingContext.Observe(doc);
                if ((string)after["mode"] != "unknown" || (bool)after["stable"])
                    throw new InvalidOperationException("An unsupported provider loaded after startup was treated as a normal model.");
                report += "\nPASS unsupported editor provider loaded after startup is unknown/unstable";
            }
            return report;
        }
    }
}
