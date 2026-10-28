using Eto.Forms;
using Rhino.Commands;
using Rhino.Input.Custom;
using Rhino.UI;
using RhinoTerminal;
using System.Text.Json;

static void Check(bool value, string message)
{
    if (!value) throw new Exception(message);
}
static Result Run(string option)
{
    GetOption.Selected = option;
    return new OpenTerminalCommand().Execute();
}
static WebView View(TerminalPanel panel) => (WebView)panel.Content!;
var failures = 0;
var total = 0;
void Test(string name, Action action)
{
    total++;
    try { action(); Console.WriteLine("PASS: " + name); }
    catch (Exception ex) { failures++; Console.WriteLine("FAIL: " + name + " — " + ex.Message); }
    finally
    {
        foreach (var session in TerminalSession.Created) session.DelayCompletionOnStop = false;
        TerminalPanel.StopAll();
        TerminalSession.Created.Clear();
        AlmondHost.Created.Clear();
        Panels.Visible = false;
        Panels.OpenCalls = 0;
    }
}

Test("restored panel and web readiness never start shell or Almond service", () =>
{
    using var panel = new TerminalPanel();
    View(panel).Receive("{\"type\":\"ready\"}");
    UITimer.TickAll();
    Check(TerminalSession.Created.Count == 0 && AlmondHost.Created.Count == 0, "Restored panel auto-started the terminal.");
});
Test("On and Off work without a panel; On is idempotent", () =>
{
    Check(Run("On") == Result.Success, "On failed.");
    Check(GetOption.LastOptions.SequenceEqual(new[] { "On", "Off", "PanelToggle" }), "Command does not offer the three requested options.");
    Check(TerminalSession.Created.Count == 1 && AlmondHost.Created.Count == 1, "On without a panel did not start one runtime.");
    Run("On");
    Check(TerminalSession.Created.Count == 1, "Repeated On restarted a live shell.");
    Run("Off");
    Check(TerminalSession.Created.Single().Stopped && AlmondHost.Created.Single().Disposed, "Off did not stop the hidden runtime.");
    Run("Off");
    Check(Panels.OpenCalls == 0 && !Panels.Visible, "On/Off changed panel visibility.");
});
Test("PanelToggle changes visibility without starting a stopped terminal", () =>
{
    Run("PanelToggle");
    Check(Panels.Visible, "PanelToggle did not open the panel.");
    Run("PanelToggle");
    Check(!Panels.Visible, "PanelToggle did not hide the panel.");
    Check(TerminalSession.Created.Count == 0 && AlmondHost.Created.Count == 0, "PanelToggle started the runtime.");
});
Test("On after Off starts a fresh shell while prior asynchronous exit drains", () =>
{
    Run("On");
    var previous = TerminalSession.Created.Single();
    previous.DelayCompletionOnStop = true;
    Run("Off");
    Check(previous.Stopped && !previous.Completion!.IsCompleted, "Fixture did not model asynchronous shutdown.");
    Run("On");
    Check(TerminalSession.Created.Count == 2 && !TerminalSession.Created.Last().Stopped, "On was ignored while the stopped shell drained.");
});
Test("visible panel input, Off and restart keep execution independent of visibility", () =>
{
    using var panel = new TerminalPanel();
    var web = View(panel);
    web.Receive("{\"type\":\"ready\"}");
    Panels.Visible = true;
    Run("On");
    web.Receive("{\"type\":\"input\",\"text\":\"almond resume\\r\"}");
    Check(TerminalSession.Created.Single().Input.SequenceEqual(new[] { "almond resume\r" }), "Existing terminal input path was bypassed.");
    Run("Off");
    Check(TerminalSession.Created.Single().Stopped && Panels.Visible, "Off failed to stop or hid the panel.");
    web.Receive("{\"type\":\"ready\"}");
    Check(TerminalSession.Created.Count == 1, "Readiness restarted the stopped shell.");
    Run("On");
    Check(TerminalSession.Created.Count == 2 && !TerminalSession.Created.Last().Stopped, "On after Off failed.");
});
Test("closing the view keeps runtime alive and hidden output/document checks drain", () =>
{
    Run("On");
    var session = TerminalSession.Created.Single();
    using (var panel = new TerminalPanel()) View(panel).Receive("{\"type\":\"ready\"}");
    Check(!session.Stopped && !AlmondHost.Created.Single().Disposed, "Disposing a view stopped the runtime.");
    for (var i = 0; i < 12; i++)
    {
        session.Output.Writer.TryWrite(new string('x', 32768));
        UITimer.TickAll();
    }
    session.Output.Writer.TryWrite("HIDDEN-PROOF");
    UITimer.TickAll();
    Check(!session.Output.Reader.TryRead(out _), "Hidden output was not drained.");
    Check(AlmondHost.Created.Single().Checks > 0, "Hidden runtime skipped document checks.");
    using var reopened = new TerminalPanel();
    View(reopened).Receive("{\"type\":\"ready\"}");
    UITimer.TickAll();
    var replay = string.Join("", View(reopened).Scripts);
    Check(replay.Contains("HIDDEN-PROOF"), "Reopened view lost recent hidden output.");
    Check(replay.Length < 150000, "Hidden transcript is unbounded.");
    TerminalPanel.StopAll();
    Check(session.Stopped && AlmondHost.Created.Single().Disposed, "Plugin shutdown did not stop a hidden runtime.");
});
Test("canceling the command has no lifecycle or panel effect", () =>
{
    Check(Run("cancel") == Result.Cancel, "Canceled command did not return Cancel.");
    Check(Panels.OpenCalls == 0 && TerminalSession.Created.Count == 0, "Canceled command changed state.");
});
Test("panel reports the Rhino PID independently of shell and Almond status", () =>
{
    using var panel = new TerminalPanel();
    var web = View(panel);
    web.Receive("{\"type\":\"ready\"}");
    void CheckPid(string expectedStatus = "")
    {
        UITimer.TickAll();
        const string prefix = "window.RhinoTerminal.meta(";
        var script = web.Scripts.Last(value => value.StartsWith(prefix));
        using var json = JsonDocument.Parse(script.Substring(prefix.Length, script.Length - prefix.Length - 1));
        Check(json.RootElement.GetProperty("rhino_pid").GetInt32() == Environment.ProcessId,
            "The panel omitted its Rhino process identity or substituted the child shell PID.");
        if (expectedStatus != "")
            Check(json.RootElement.GetProperty("status").GetString() == expectedStatus, "Fixture status update did not reach the panel.");
    }
    CheckPid();
    Run("On");
    AlmondHost.Created.Single().Report("Almond connected");
    CheckPid("Almond connected");
    Run("Off");
    CheckPid();
});
Console.WriteLine($"Terminal control contracts: {total - failures}/{total} passed.");
return failures == 0 ? 0 : 1;
