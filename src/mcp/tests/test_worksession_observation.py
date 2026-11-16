"""Exercise the native Worksession observation without loading Rhino."""
import pytest

from test_stage2_native_feedback import build_host


@pytest.fixture(scope="module")
def worksession_host(tmp_path_factory):
    return build_host(tmp_path_factory.mktemp("worksession"), r'''
using System;
using System.IO;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using RhinoAlmondBridge;

var scenario = args[0];
var document = new RhinoDoc { Path = @"C:\Models\Active.3dm" };
var work = document.Worksession;
work.RuntimeSerialNumber = 15;
work.ModelCount = 3;
work.Paths = new[] { @"c:/models/reference/../ACTIVE.3dm", @"C:\Models\Wing.3dm", @"D:\Details\Wing.3dm" };
if (scenario == "none") {
    work.RuntimeSerialNumber = 0;
    work.ModelCount = 0;
    work.Paths = Array.Empty<string>();
}
if (scenario == "failed") work.Paths = null;
if (scenario == "native_failed") work.Throw = true;
if (scenario == "wrong_owner") work.Document = new RhinoDoc { RuntimeSerialNumber = 12 };
if (scenario == "missing_active") work.Paths[0] = @"C:\Models\Unrelated.3dm";
if (scenario == "unreadable_session") {
    work.ModelCount = 0;
    work.Paths = Array.Empty<string>();
}
if (scenario == "unsaved") {
    document.Path = "";
    work.ModelCount = 2;
    work.Paths = new[] { @"C:\Models\Wing.3dm" };
}
var warnings = new JArray();
var files = WorksessionObservation.Read(document, warnings);
Console.WriteLine(new JObject { ["files"] = files, ["warnings"] = warnings }.ToString(Formatting.None));

namespace Rhino {
    public sealed class RhinoDoc {
        public RhinoDoc() { Worksession = new DocObjects.Worksession { Document = this }; }
        public string Path { get; set; }
        public uint RuntimeSerialNumber { get; set; } = 7;
        public DocObjects.Worksession Worksession { get; }
    }
}
namespace Rhino.DocObjects {
    public sealed class Worksession {
        public RhinoDoc Document { get; set; }
        public uint RuntimeSerialNumber { get; set; }
        public int ModelCount { get; set; }
        public string[] Paths { get; set; }
        public bool Throw { get; set; }
        public string[] ModelPaths => Throw ? throw new IOException("Native read failed.") : Paths;
    }
}
''', ["features/context/native/WorksessionObservation.cs"])


def test_worksession_keeps_distinct_attached_files_and_excludes_active_identity(worksession_host):
    assert worksession_host("attached") == {
        "files": [
            {"file_name": "Wing.3dm", "file_path": r"C:\Models\Wing.3dm"},
            {"file_name": "Wing.3dm", "file_path": r"D:\Details\Wing.3dm"},
        ],
        "warnings": [],
    }


def test_worksession_distinguishes_an_empty_session_from_failed_reads(worksession_host):
    assert worksession_host("none") == {"files": [], "warnings": []}
    for scenario in ("failed", "native_failed", "unreadable_session", "wrong_owner", "missing_active"):
        result = worksession_host(scenario)
        assert result["files"] is None
        assert len(result["warnings"]) == 1
        assert result["warnings"][0].startswith("worksession_files:")


def test_worksession_keeps_attachments_when_current_model_is_unsaved(worksession_host):
    assert worksession_host("unsaved") == {
        "files": [{"file_name": "Wing.3dm", "file_path": r"C:\Models\Wing.3dm"}],
        "warnings": [],
    }
