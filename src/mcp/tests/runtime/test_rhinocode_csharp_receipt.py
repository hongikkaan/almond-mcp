"""Compile the actual C# wrapper with an offline Rhino API stub; never load Rhino."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from xml.sax.saxutils import escape

import pytest

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def csharp_wrapper(tmp_path_factory):
    sdk = os.environ.get("ALMOND_TEST_DOTNET") or ROOT / "src/rhp/RhinoTerminal/data/sdk/dotnet.exe"
    if not Path(sdk).is_file():
        sdk = shutil.which("dotnet")
    assert sdk, "The offline C# wrapper fixture requires the .NET 8 SDK."
    directory = tmp_path_factory.mktemp("csharp-wrapper")
    assembly = ROOT / "src/rhp/RhinoAlmondBridge/plugin-runtime/Newtonsoft.Json.dll"
    assert assembly.is_file(), "The shipped Newtonsoft.Json dependency is required."
    (directory / "Fixture.csproj").write_text('''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework></PropertyGroup>
  <ItemGroup><Reference Include="Newtonsoft.Json"><HintPath>''' + escape(str(assembly)) + '''</HintPath></Reference></ItemGroup>
</Project>''', encoding="utf-8")
    (directory / "NuGet.Config").write_text(
        '<configuration><packageSources><clear /></packageSources></configuration>', encoding="utf-8")
    text = (ROOT / "src/mcp/runtime/rhinocode_csharp.cs.txt").read_text(encoding="utf-8")
    text = "\n".join(line for line in text.splitlines() if not line.startswith("#r "))
    text = text.replace('Convert.FromBase64String("__PAYLOAD__")', 'File.ReadAllBytes(args[0])')
    # Supply the fixture process identity and API stub, as the Python fixture does.
    text = text.replace('var __directory =', '''__request["target"]["pid"] = Environment.ProcessId;
__request["target"]["process_start_ticks"] = Process.GetCurrentProcess().StartTime.ToUniversalTime().Ticks.ToString();
RhinoDoc.ActiveDoc = new RhinoDoc { Path = (string)__request["target"]["model_path"], RuntimeSerialNumber = 7 };
var __directory =''')
    text = text.replace("__USER_BODY__", '''
        doc.Marker = "changed";
        if ((string)__payload["scenario"] == "broken_error") throw new BrokenException();
        if ((string)__payload["scenario"] != "success")
            throw new Exception(String.Concat(System.Linq.Enumerable.Repeat(Char.ConvertFromUtf32(0x1f600), 4000)));
        result_json = "{\\"answer\\":42}";
''')
    text = text.replace("sealed class AlmondRhinoCodeLog", '''
Console.WriteLine(new JObject { ["marker"] = doc.Marker, ["undo_ended"] = doc.Ended,
    ["redraw_enabled"] = doc.Views.RedrawEnabled }.ToString(Formatting.None));
sealed class AlmondRhinoCodeLog''')
    text += '''
sealed class BrokenException : Exception {
    public override string Message => throw new Exception("Message formatting failed");
    public override string ToString() => throw new Exception("Trace formatting failed");
}
namespace Rhino {
    public static class RhinoApp { public static bool IsOnMainThread => true; }
    public sealed class Views {
        public bool RedrawEnabled { get; set; } = true;
        public void Redraw() { }
    }
    public sealed class RhinoDoc {
        public static RhinoDoc ActiveDoc { get; set; }
        public string Path { get; set; }
        public uint RuntimeSerialNumber { get; set; }
        public uint CurrentUndoRecordSerialNumber { get; private set; }
        public Views Views { get; } = new Views();
        public string Marker { get; set; }
        public bool Ended { get; private set; }
        public uint BeginUndoRecord(string name) { CurrentUndoRecordSerialNumber = 9; return 9; }
        public bool EndUndoRecord(uint serial) {
            if (serial != 9) throw new Exception("Wrong Undo owner");
            Ended = true; CurrentUndoRecordSerialNumber = 0; return true;
        }
    }
}
'''
    (directory / "Program.cs").write_text(text, encoding="utf-8")
    built = subprocess.run([str(sdk), "build", "Fixture.csproj", "-c", "Release", "--nologo",
                            "-p:UseSharedCompilation=false", "-p:NuGetAudit=false", "-nodeReuse:false"],
                           cwd=directory, capture_output=True, text=True)
    assert built.returncode == 0, built.stdout + built.stderr
    return sdk, directory / "bin/Release/net8.0/Fixture.dll"


@pytest.mark.parametrize("scenario", ["unicode_error", "large_identity", "broken_error", "success"])
def test_csharp_completion_preserves_identity_mutation_and_result(csharp_wrapper, tmp_path, scenario):
    request = dict(token="a" * 32, operation_id="b" * 32, request_id="c" * 32,
        nonce="d" * 32, source_hash="e" * 64,
        target=dict(pid=1, process_start_ticks="1", document_serial=7,
                    model_path=str(tmp_path / "path-only.3dm"),
                    pipe_id="p" * (53000 if scenario == "large_identity" else 10)))
    payload = dict(request=request, directory=str(tmp_path), project_root=str(tmp_path),
                   artifact_dir=str(tmp_path), result_limit=1048576, scenario=scenario)
    path = tmp_path / "payload.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    sdk, fixture = csharp_wrapper
    ran = subprocess.run([str(sdk), str(fixture), str(path)], capture_output=True, text=True)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert json.loads(ran.stdout) == dict(marker="changed", undo_ended=True, redraw_enabled=True)
    receipt = tmp_path / "child-complete.json"
    assert receipt.stat().st_size <= 65536
    final = json.loads(receipt.read_text(encoding="utf-8"))
    for key in ("token", "operation_id", "request_id", "nonce", "source_hash"):
        assert final[key] == request[key]
    assert final["target"]["model_path"] == request["target"]["model_path"]
    assert final["target"]["pipe_id"] == request["target"]["pipe_id"]
    assert final["execution_complete"] and final["user_code_started"]
    assert final["undo"]["owned"] == 9 and final["undo"]["ended"]
    if scenario == "success":
        raw = (tmp_path / "result.json").read_bytes()
        assert final["status"] == "success" and final["mutation_state"] == "completed"
        assert final["result_sha256"] == hashlib.sha256(raw).hexdigest()
        assert json.loads(raw) == {"answer": 42}
    else:
        assert final["status"] == "error" and final["mutation_state"] == "partial"
        assert final["error"]["type"] == ("BrokenException" if scenario == "broken_error" else "Exception")
        assert final["error"]["stage"] == "user_code"
        if scenario == "large_identity":
            assert final["diagnostics_truncated"] is True
        else:
            for key, maximum in (("message", 4000), ("traceback", 8000)):
                assert len(json.dumps(final["error"][key], ensure_ascii=True).encode("ascii")) <= maximum
