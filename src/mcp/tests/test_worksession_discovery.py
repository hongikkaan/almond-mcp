"""Worksession attachment discovery with controlled data and no live Rhino document."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import mcp_server

from almond_mcp.features.context.context_query import context_catalogues, observe_context, query
from test_layout_viewport_state import method


def test_initial_project_info_separates_live_attachments_from_registered_files(monkeypatch, tmp_path):
    registered = {"filename": "registered.3dm", "file_name": "registered.3dm", "description": "Plan source"}
    native = {"status": "success", "capabilities": {"context_sections": 4}, "warnings": [],
              "document": {"name": "active.3dm", "path": str(tmp_path / "active.3dm")},
              "named_views": [], "layouts": [], "layers": [],
              "worksession": {"attachments": [{"filename": "attached.3dm", "path": str(tmp_path / "attached.3dm")}]}}
    binding = {"label": "A"}
    locations = {"project_dir": str(tmp_path), "model_path": str(tmp_path / "active.3dm"),
                 "state_db": str(tmp_path / ".almond" / "scene.sqlite3")}
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(mcp_server, "read_binding", lambda *_: (binding, locations))
    monkeypatch.setattr(mcp_server, "verify_process", lambda _: None)
    tools, calls = {}, []

    class CaptureTools:
        def tool(self, *, name, **_):
            def register(function):
                tools[name] = function
                return function
            return register

    def send(payload):
        calls.append(json.loads(payload))
        return json.dumps(native)

    store = SimpleNamespace(list_project_files=lambda limit, offset: {
        "files": [registered], "total": 1, "limit": limit, "offset": offset, "truncated": False})
    runtime = SimpleNamespace(workspace=SimpleNamespace(store=store, current=lambda: {"artifact_dir": ""}))
    asyncio.run(mcp_server.configure_project_context(CaptureTools(), SimpleNamespace(session="fixture", token="fixture"),
                                                    binding, locations, sender=send, runtime=runtime))
    result = tools["context_04-get_project_info"]()
    assert result["project"]["files"] == [registered]
    assert result["worksession"] == {"attachments": [{"filename": "attached.3dm", "path": "attached.3dm"}]}
    assert result["layers"] == "" and result["layouts"] == [] and result["named_views"] == []
    assert len(calls) == 1
    assert calls[0]["sections"] == ["document", "named_views", "layouts", "layers", "worksession"]


def test_worksession_projection_preserves_empty_unknown_and_relative_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("ALMOND_PROJECT_ROOT", str(tmp_path))
    for value in ({"attachments": []}, None,
                  {"attachments": [{"filename": "ref.3dm", "path": str(tmp_path / "ref.3dm")}]}):
        native = {"status": "success", "capabilities": {"context_sections": 4},
                  "worksession": value, "warnings": ["worksession: unavailable"] if value is None else []}
        send = lambda _: json.dumps(native)
        projected = json.loads(query(send, ["worksession"]))
        expected = {"attachments": [{"filename": "ref.3dm", "path": "ref.3dm"}]} if value and value["attachments"] else value
        assert projected["worksession"] == expected
        assert projected["warnings"] == native["warnings"]
        assert context_catalogues(observe_context(send, ["worksession"]), ["worksession"])["worksession"] == value
    old = lambda _: json.dumps({"status": "success", "capabilities": {"context_sections": 3}})
    assert json.loads(query(old, ["worksession"]))["error_code"] == "unsupported_context"


def test_native_worksession_attachment_collection_uses_only_rhino8_model_paths(tmp_path):
    sdk = os.environ.get("ALMOND_TEST_DOTNET")
    assert sdk, "Run through run_tests.ps1 to select the .NET 8 SDK."
    source = (Path(__file__).parents[1] / "features/context/native/DocumentObservation.cs").read_text(encoding="utf-8")
    methods = "\n".join(method(source, name) for name in ("ReadWorksession", "NormalizeWorksessionPath", "Observe"))
    (tmp_path / "Program.cs").write_text(WORKSESSION_HARNESS.replace("// PRODUCTION_METHODS", methods), encoding="utf-8")
    project = tmp_path / "WorksessionDiscovery.csproj"
    project.write_text('''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework><Nullable>disable</Nullable></PropertyGroup>
  <ItemGroup><Reference Include="Newtonsoft.Json"><HintPath>$(MSBuildBinPath)/Newtonsoft.Json.dll</HintPath></Reference></ItemGroup>
</Project>''', encoding="utf-8")
    built = subprocess.run([sdk, "build", str(project), "-c", "Release", "--nologo",
                            "-p:UseSharedCompilation=false", "-p:NuGetAudit=false", "-nodeReuse:false"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert built.returncode == 0, built.stdout + built.stderr
    run = subprocess.run([sdk, str(tmp_path / "bin/Release/net8.0/WorksessionDiscovery.dll")],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS:" in run.stdout


WORKSESSION_HARNESS = r'''
using System;
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json.Linq;
sealed class Worksession { public string[] ModelPaths; }
sealed class RhinoDoc { public string Path; public Worksession Worksession; }
static class Program {
    // PRODUCTION_METHODS
    static void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
    static void Reject(Action read) {
        try { read(); } catch (InvalidOperationException) { return; }
        throw new Exception("Unavailable or invalid paths were accepted as an empty attachment list.");
    }
    static void RejectSection(RhinoDoc doc, string message) {
        var warnings = new JArray();
        var paths = doc.Worksession == null ? null : doc.Worksession.ModelPaths;
        var section = Observe("worksession", () => ReadWorksession(doc), warnings);
        Check(section.Type == JTokenType.Null, message + ": partial valid rows escaped a failed section.");
        Check(warnings.Count == 1 && ((string)warnings[0]).StartsWith("worksession: "), message + ": missing observation warning.");
        Check(doc.Worksession == null || doc.Worksession.ModelPaths == paths, message + ": input paths were mutated.");
    }
    static void Main() {
        var paths = new [] { @"C:\project\ACTIVE.3dm", @"C:\project\refs\..\ref.3dm", @"c:/PROJECT/REF.3dm", @"C:\other\ref.3dm" };
        var doc = new RhinoDoc { Path = @"c:/PROJECT/active.3dm", Worksession = new Worksession { ModelPaths = paths } };
        var attachments = (JArray)ReadWorksession(doc)["attachments"];
        Check(attachments.Count == 2, "The active model or duplicate path was included, or equal filenames were merged.");
        Check((string)attachments[0]["filename"] == "ref.3dm", "Attachment filename changed.");
        Check((string)attachments[0]["path"] == @"C:\project\ref.3dm", "Attachment path was not normalized.");
        Check(doc.Worksession.ModelPaths == paths && paths.Length == 4, "Worksession was mutated.");
        doc.Path = "";
        Check(((JArray)ReadWorksession(doc)["attachments"]).Count == 3, "Unsaved active document hid an attachment.");
        doc.Worksession.ModelPaths = Array.Empty<string>();
        Check(((JArray)ReadWorksession(doc)["attachments"]).Count == 0, "Empty attachment list changed.");
        var emptyWarnings = new JArray();
        Check(((JArray)Observe("worksession", () => ReadWorksession(doc), emptyWarnings)["attachments"]).Count == 0 && emptyWarnings.Count == 0,
            "Empty attachment list was confused with an observation failure.");
        doc.Path = @"C:\project\active.3dm";
        doc.Worksession.ModelPaths = new [] { @"C:\project\active.3dm" };
        Check(((JArray)ReadWorksession(doc)["attachments"]).Count == 0, "Active-only Worksession is not empty.");
        doc.Worksession.ModelPaths = null;
        Reject(() => ReadWorksession(doc));
        RejectSection(doc, "unavailable ModelPaths");
        foreach (var invalid in new [] { "ref.3dm", @"C:ref.3dm", @"\project\ref.3dm", "", "   ", null,
            "C:\\project\\bad\0.3dm", @"C:\", @"C:\project\..\", @"\\server\share", @"\\server\share\", @"C:\project\folder\",
            @"C:\refs\bad?.3dm", @"C:\bad<>\ref.3dm", @"C:\refs\bad*.3dm", @"C:\bad|folder\ref.3dm", "C:\\refs\\bad\".3dm",
            "C:\\refs\\bad\u0001.3dm", "C:\\bad\u001f\\ref.3dm", @"C:\bad<>\..\ref.3dm", @"C:\refs\ref.3dm:stream",
            @"\\bad?server\share\ref.3dm", @"\\server\bad*share\ref.3dm", @"\\?\UNC\bad<server\share\ref.3dm",
            @"\\?\UNC\server\bad>share\ref.3dm", @"\\.\UNC\server\bad|share\ref.3dm", @"\\?\C:\refs\bad?.3dm", @"\\?\C:ref.3dm" }) {
            foreach (var mixed in new [] {
                new [] { invalid },
                new [] { @"C:\does-not-exist\valid.3dm", invalid },
                new [] { invalid, @"C:\does-not-exist\valid.3dm" } }) {
                doc.Worksession.ModelPaths = mixed;
                RejectSection(doc, "invalid path alone or mixed with valid paths");
            }
        }
        doc.Worksession.ModelPaths = new [] { @"C:\does-not-exist\ref.3dm", @"\\server\share\ref.3dm" };
        var warnings = new JArray();
        var unverified = Observe("worksession", () => ReadWorksession(doc), warnings);
        Check(((JArray)unverified["attachments"]).Count == 2 && warnings.Count == 0,
            "API-reported paths were filtered or interpreted as filesystem load status.");
        Check((string)unverified["attachments"][1]["path"] == @"\\server\share\ref.3dm", "UNC path changed.");
        foreach (var valid in new [] { @"C:\refs\CON.3dm", @"C:\refs\COM1.3dm", @"C:\refs\LPT1.3dm",
            @"\\?\C:\refs\ref.3dm", @"\\?\UNC\server\share\ref.3dm", @"\\.\C:\refs\ref.3dm", @"\\.\UNC\server\share\ref.3dm",
            @"\\?\C:\refs\ref.3dm.", @"\\?\C:\refs\dir.\ref.3dm" }) {
            doc.Worksession.ModelPaths = new [] { valid };
            var prefixWarnings = new JArray();
            var accepted = Observe("worksession", () => ReadWorksession(doc), prefixWarnings);
            Check(prefixWarnings.Count == 0 && ((JArray)accepted["attachments"]).Count == 1, "Valid namespace/drive syntax was rejected.");
            Check((string)accepted["attachments"][0]["path"] == valid, "Namespace or reserved-name API path was changed.");
        }
        Check(NormalizeWorksessionPath(@"C:\refs\ref.3dm.") == @"C:\refs\ref.3dm" &&
            NormalizeWorksessionPath("C:\\refs\\ref.3dm ") == @"C:\refs\ref.3dm", "Ordinary trailing-dot/space normalization changed.");
        doc.Worksession = null;
        Reject(() => ReadWorksession(doc));
        RejectSection(doc, "unavailable Worksession");
        Console.WriteLine("PASS: active/unsaved/empty models, normalized case-insensitive deduplication, mixed-invalid atomic null/warnings, unverified API paths, no mutation");
    }
}
'''
