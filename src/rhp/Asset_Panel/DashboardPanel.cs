#nullable enable
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using RuntimeEnvironment = AlmondEngine.RuntimeEnvironment;
using Eto.Drawing;
using Eto.Forms;
using Rhino;
using Rhino.Commands;

namespace RhinoAlmondBridge;

// Existing Rhino dock/float UI; the database viewer remains the same local web app.
[Guid("8636a0f8-b78c-4c47-b09f-bae925ddbd64")]
public sealed class AlmondDashboardPanel : Panel, Rhino.UI.IPanel
{
    public static Guid PanelId => typeof(AlmondDashboardPanel).GUID;
    static readonly HashSet<AlmondDashboardPanel> panels = new();
    static DashboardDocumentSession? documents;
    readonly WebView web = new() { BrowserContextMenuEnabled = false, Visible = false };
    const string Starting = "Dashboard 시작 중…";
    readonly Label notice = new() { Text = Starting, Wrap = WrapMode.Word };
    readonly Button retry = new() { Text = "현재 문서 DB 다시 열기" };
    readonly Panel status = new();
    bool disposed, opening, documentEvents;
    int request;
    Uri? loadedAddress;

    public AlmondDashboardPanel()
    {
        panels.Add(this);
        HookDocumentEvents();
        MinimumSize = new Size(320, 240);
        var statusLayout = new DynamicLayout { Padding = new Padding(8), Spacing = new Size(4, 4) };
        statusLayout.Add(notice, xscale: true);
        statusLayout.Add(retry);
        status.Content = statusLayout;
        // Collapse the whole status row once the page loads, with no padding
        // around the viewer. Keep the WebView attached during navigation.
        Content = new TableLayout(
            new TableRow(new TableCell(status, scaleWidth: true)),
            new TableRow(new TableCell(web, scaleWidth: true)) { ScaleHeight = true })
        { Padding = new Padding(0), Spacing = new Size(0, 0) };
        retry.Click += (_, _) => Open(reselect: true);
        web.DocumentLoading += (_, e) => {
            if (e.Uri == null || documents?.Runtime?.AllowsNavigation(e.Uri) != true) e.Cancel = true;
        };
        web.DocumentLoaded += (_, e) => {
            // Keep the previous project's DOM hidden until the newly selected
            // server page is loaded, including a slow local navigation.
            if (!disposed && loadedAddress != null && e.Uri != null &&
                documents?.Runtime?.AllowsNavigation(e.Uri) == true)
            {
                status.Visible = false;
                web.Visible = true;
            }
        };
        web.OpenNewWindow += (_, _) => { /* Dashboard does not navigate outside its own origin. */ };
        Open();
    }

    void DocumentChanged(object? sender, DocumentEventArgs e) => RefreshDocument();
    void DocumentSaved(object? sender, DocumentSaveEventArgs e) => RefreshDocument();
    void HookDocumentEvents()
    {
        if (documentEvents) return;
        documentEvents = true;
        RhinoDoc.ActiveDocumentChanged += DocumentChanged;
        RhinoDoc.EndSaveDocument += DocumentSaved;
        RhinoDoc.CloseDocument += DocumentClosing;
    }
    void UnhookDocumentEvents()
    {
        if (!documentEvents) return;
        documentEvents = false;
        RhinoDoc.ActiveDocumentChanged -= DocumentChanged;
        RhinoDoc.EndSaveDocument -= DocumentSaved;
        RhinoDoc.CloseDocument -= DocumentClosing;
    }
    void RefreshDocument()
    {
        if (!panels.Contains(this) || disposed) return;
        var doc = RhinoDoc.ActiveDoc;
        var current = documents?.Context;
        bool changed = current?.SerialNumber != (doc?.RuntimeSerialNumber ?? 0) ||
            !string.Equals(current?.DocumentPath, doc?.Path, StringComparison.OrdinalIgnoreCase);
        Open(reselect: changed);
    }
    void DocumentClosing(object? sender, DocumentEventArgs e)
    {
        if (!panels.Contains(this) || disposed || e.Document?.RuntimeSerialNumber != documents?.Context?.SerialNumber) return;
        var context = documents!.Select(null, 0);
        foreach (var panel in panels) panel.Clear(context.Status);
    }
    void Clear(string status)
    {
        request++;
        opening = false;
        loadedAddress = null;
        ShowStatus(status);
        retry.Enabled = true;
    }
    void ShowStatus(string message)
    {
        web.Visible = false;
        notice.Text = message;
        status.Visible = true;
    }
    internal void Open(bool reselect = false)
    {
        if (disposed) return;
        documents ??= new DashboardDocumentSession(database => new DashboardRuntime(
            RuntimeEnvironment.RuntimeDirectory(typeof(AlmondDashboardPanel).Assembly.Location), database: database));
        var previous = documents.Runtime;
        var doc = RhinoDoc.ActiveDoc;
        var context = documents.Select(doc?.Path, doc?.RuntimeSerialNumber ?? 0, reselect);
        if (!ReferenceEquals(previous, documents.Runtime) || documents.Runtime == null)
            foreach (var panel in panels) panel.Clear(context.DatabasePath == null ? context.Status : Starting);
        foreach (var panel in panels) panel.ShowCurrent();
    }
    async void ShowCurrent()
    {
        var own = documents?.Runtime;
        if (disposed || own == null || opening) return;
        int version = ++request;
        opening = true;
        retry.Enabled = false;
        if (!web.Visible) ShowStatus(Starting);
        try
        {
            var url = await own.StartAsync();
            if (disposed || version != request || !ReferenceEquals(documents?.Runtime, own)) return;
            // Showing the same panel must not reset its filters or expanded Steps.
            if (loadedAddress != url || web.Url == null || !own.AllowsNavigation(web.Url))
            {
                ShowStatus(Starting);
                loadedAddress = url;
                web.Url = url;
            }
        }
        catch (Exception ex)
        {
            if (!disposed && version == request)
            {
                ShowStatus("Dashboard를 열지 못했습니다. " +
                    (ex is OperationCanceledException ? "시작 시간이 초과됐습니다. 다시 시도하세요." : ex.Message));
            }
        }
        finally { if (version == request) { opening = false; if (!disposed) retry.Enabled = true; } }
    }

    protected override void Dispose(bool disposing)
    {
        disposed = true;
        request++;
        if (disposing)
        {
            UnhookDocumentEvents();
            panels.Remove(this);
            if (panels.Count == 0) StopAll();
        }
        base.Dispose(disposing);
    }

    public void PanelShown(uint documentSerialNumber, Rhino.UI.ShowPanelReason reason)
    {
        panels.Add(this);
        HookDocumentEvents();
        Open();
    }
    public void PanelHidden(uint documentSerialNumber, Rhino.UI.ShowPanelReason reason) { }
    public void PanelClosing(uint documentSerialNumber, bool onCloseDocument)
    {
        request++;
        opening = false;
        UnhookDocumentEvents();
        panels.Remove(this);
        if (panels.Count == 0) StopAll();
    }

    internal static void StopAll()
    {
        foreach (var panel in panels)
        {
            panel.Clear("Dashboard 종료됨");
            panel.UnhookDocumentEvents();
        }
        documents?.Dispose();
        documents = null;
    }
}

public sealed class AlmondDashboardCommand : Rhino.Commands.Command
{
    static bool panelRegistered;

    public override string EnglishName => "AlmondDashboard";

    void EnsurePanelRegistered()
    {
        if (panelRegistered) return;
        // Rhino discovers public commands through PlugIn.CreateCommands.
        // The feature owns panel registration rather than extending Bridge OnLoad.
        Rhino.UI.Panels.RegisterPanel(PlugIn, typeof(AlmondDashboardPanel), "Dashboard",
            typeof(AlmondDashboardPanel).Assembly, "RhinoAlmondBridge.Resources.almond.ico", Rhino.UI.PanelType.PerDoc);
        RhinoApp.Closing += OnRhinoClosing;
        panelRegistered = true;
    }

    static void OnRhinoClosing(object? sender, EventArgs e)
    {
        RhinoApp.Closing -= OnRhinoClosing;
        try { AlmondDashboardPanel.StopAll(); }
        catch (Exception ex) { RhinoApp.WriteLine("AlmondDashboard: {0}", ex.Message); }
    }

    static void OpenPanel(RhinoDoc? doc)
    {
        var existing = doc == null ? null : Rhino.UI.Panels.GetPanel<AlmondDashboardPanel>(doc);
        Rhino.UI.Panels.OpenPanel(AlmondDashboardPanel.PanelId, true);
        // New panels select in their constructor. Explicit reopening resets a
        // manually selected DB back to the active Rhino document's project DB.
        existing?.Open(reselect: true);
    }
    protected override Result RunCommand(RhinoDoc doc, RunMode mode)
    {
        try { EnsurePanelRegistered(); OpenPanel(doc); return Result.Success; }
        catch (Exception ex) { RhinoApp.WriteLine("AlmondDashboard: {0}", ex.Message); return Result.Failure; }
    }
}
