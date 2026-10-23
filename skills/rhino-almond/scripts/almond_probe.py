"""Prepare a bounded Rhino helper call and read its identified JSON report.

This program does not connect to Rhino or execute a script. Use the prepared
source with the existing Almond execute_rhino_script tool.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import uuid

SCHEMA = "rhino-almond-job/1"
# Entries name bundled code and a read-only expression, not arbitrary user code.
TOOLS = {
    "sections": (["AlmondTerrain.cs"], "AlmondTerrain.Sections(doc, options)"),
    "vertical-probe": (["AlmondTerrain.cs"], "AlmondTerrain.VerticalProbe(doc, options)"),
    "joint-pairs": (["AlmondJoints.cs"], "AlmondJoints.AuditPairs(doc, options)"),
    "outline": (["AlmondSpatial.cs"], "AlmondSpatial.Outline(doc, options)"),
    "resolve-block": (["AlmondSpatial.cs"],
        'AlmondSpatial.ResolveBlock(doc, options["path"].Values<string>().Select(Guid.Parse).ToArray())'),
}
RUNNER = r'''
public class AlmondProbeScript
{
    public static List<Guid> Run(RhinoDoc doc)
    {
        const string expectedModel = __MODEL__;
        const string reportPath = __REPORT__;
        var report = new JObject {
            ["schema"] = "rhino-almond-result/1",
            ["run_id"] = __RUN_ID__, ["tool"] = __TOOL__,
            ["expected_model_path"] = expectedModel,
            ["started_utc"] = DateTime.UtcNow.ToString("o"),
            ["status"] = "running"
        };
        if (File.Exists(reportPath) || File.Exists(reportPath + ".partial"))
            throw new InvalidOperationException("This run already has a report or partial report. Inspect it; prepare a new run if needed.");
        try {
            if (doc == null || String.IsNullOrEmpty(doc.Path) ||
                !String.Equals(Path.GetFullPath(doc.Path), Path.GetFullPath(expectedModel), StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Connected Rhino document differs from the prepared model_path.");
            report["model_path"] = doc.Path;
            report["document_serial"] = doc.RuntimeSerialNumber;
            report["model_units"] = doc.ModelUnitSystem.ToString();
            report["absolute_tolerance_model_units"] = doc.ModelAbsoluteTolerance;
            var options = JObject.Parse(__OPTIONS__);
            report["data"] = __CALL__;
            report["status"] = "ok";
        } catch (Exception ex) {
            report["status"] = "error";
            report["error_type"] = ex.GetType().FullName;
            report["message"] = ex.Message;
            report["finished_utc"] = DateTime.UtcNow.ToString("o");
            WriteReport(reportPath, report);
            throw;
        }
        report["finished_utc"] = DateTime.UtcNow.ToString("o");
        WriteReport(reportPath, report);
        return new List<Guid>();
    }

    static void WriteReport(string path, JObject report)
    {
        using (var file = new FileStream(path + ".partial", FileMode.CreateNew, FileAccess.Write, FileShare.None))
        using (var writer = new StreamWriter(file, new System.Text.UTF8Encoding(false))) {
            writer.Write(report.ToString(Newtonsoft.Json.Formatting.None));
        }
        File.Move(path + ".partial", path);
    }
}
'''

def reject_constant(value):
    raise ValueError("Non-finite JSON number: " + value)

def load_json(path, max_bytes=262144):
    path = Path(path)
    if path.stat().st_size > max_bytes:
        raise ValueError("JSON exceeds the read budget: " + str(path))
    return json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=reject_constant)

def absolute_path(value, field):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise ValueError(field + " must be a non-empty absolute path.")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(field + " must be absolute; use project_info's actual paths.")
    return path.resolve()

def compose_source(tool, options, model, result, run_id, scripts_dir=None):
    scripts_dir = Path(scripts_dir or Path(__file__).parent)
    if tool not in TOOLS:
        raise ValueError("Unknown tool: " + str(tool))
    if not isinstance(options, dict):
        raise ValueError("options must be a JSON object.")
    if tool == "resolve-block":
        if set(options) != {"path"} or not isinstance(options["path"], list) or not 1 <= len(options["path"]) <= 65:
            raise ValueError("resolve-block requires options with a path array of 1..65 GUID strings only.")
        for value in options["path"]:
            if not isinstance(value, str):
                raise ValueError("Every path entry must be a GUID string.")
            uuid.UUID(value)
    filenames, expression = TOOLS[tool]
    usings = {
        "using System;", "using System.Collections.Generic;", "using System.Linq;",
        "using System.IO;", "using Rhino;", "using Newtonsoft.Json.Linq;"
    }
    bodies = []
    for filename in filenames:
        source = (scripts_dir / filename).read_text(encoding="utf-8-sig")
        body = []
        for line in source.splitlines():
            if re.fullmatch(r"using [A-Za-z_][\w.]*;", line.strip()):
                usings.add(line.strip())
            else:
                body.append(line)
        bodies.append("\n".join(body))
    encoded_options = json.dumps(options, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    values = {
        "__MODEL__": str(model), "__REPORT__": str(result), "__RUN_ID__": run_id,
        "__TOOL__": tool, "__OPTIONS__": encoded_options
    }
    runner = RUNNER
    # Replace each placeholder once using a callback, so literal path/option text
    # that happens to contain a placeholder is never interpreted as a template.
    runner = re.sub(
        r"__(?:MODEL|REPORT|RUN_ID|TOOL|OPTIONS|CALL)__",
        lambda m: expression if m.group() == "__CALL__" else json.dumps(values[m.group()], ensure_ascii=True),
        runner
    )
    return "\n".join(sorted(usings)) + "\n\n" + "\n\n".join(bodies) + "\n" + runner

def prepare(job_path):
    job = load_json(job_path)
    required = {"tool", "model_path", "artifact_dir", "options"}
    if not isinstance(job, dict) or set(job) != required:
        raise ValueError("Job must contain exactly: tool, model_path, artifact_dir, options.")
    tool = job["tool"]
    if not isinstance(tool, str) or tool not in TOOLS:
        raise ValueError("tool must be one of: " + ", ".join(TOOLS))
    model = absolute_path(job["model_path"], "model_path")
    artifacts = absolute_path(job["artifact_dir"], "artifact_dir")
    if model.suffix.lower() != ".3dm" or not model.is_file():
        raise ValueError("model_path must name the saved .3dm returned by project_info.")
    if not artifacts.is_dir():
        raise ValueError("artifact_dir must be the existing directory returned by project_info.")
    run_id = uuid.uuid4().hex
    folder = artifacts / ("rhino-almond-" + tool + "-" + run_id)
    report_path = folder / "result.json"
    query = compose_source(tool, job["options"], model, report_path, run_id)
    template = (Path(__file__).parent / "AlmondProbeBootstrap.cs.in").read_text(encoding="utf-8-sig")
    if template.count("__SOURCE__") != 1:
        raise ValueError("The bundled bootstrap must contain exactly one source placeholder.")
    source = template.replace("__SOURCE__", json.dumps(query, ensure_ascii=True))
    folder.mkdir()
    script_path = folder / "script.cs"
    query_path = folder / "query.cs"
    script_path.write_text(source, encoding="utf-8", newline="\n")
    query_path.write_text(query, encoding="utf-8", newline="\n")
    manifest = {
        "schema": SCHEMA, "run_id": run_id, "tool": tool,
        "model_path": str(model), "options": job["options"],
        "script_path": str(script_path), "query_path": str(query_path), "result_path": str(report_path)
    }
    manifest_path = folder / "job.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return {"manifest_path": str(manifest_path), **manifest}

def read_result(manifest_path, max_bytes=262144):
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise ValueError("Unsupported job manifest.")
    result_path = absolute_path(manifest.get("result_path"), "result_path")
    if result_path.parent != Path(manifest_path).resolve().parent or result_path.name != "result.json":
        raise ValueError("Result path does not belong to this job.")
    if not result_path.exists():
        return {
            "status": "report_not_ready", "run_id": manifest.get("run_id"),
            "result_path": str(result_path),
            "partial_exists": Path(str(result_path) + ".partial").exists(),
            "message": "No completed report. Inspect the MCP response and Rhino state; this is not evidence of rollback."
        }, 3
    report = load_json(result_path, max_bytes)
    if not isinstance(report, dict) or report.get("schema") != "rhino-almond-result/1":
        raise ValueError("Unsupported result report.")
    for key in ("run_id", "tool"):
        if report.get(key) != manifest.get(key):
            raise ValueError("Result " + key + " does not match this job.")
    expected = absolute_path(manifest.get("model_path"), "model_path")
    if absolute_path(report.get("expected_model_path"), "expected_model_path") != expected:
        raise ValueError("Result belongs to a different expected model.")
    if report.get("status") not in ("ok", "error"):
        raise ValueError("Report has no final status.")
    if report["status"] == "ok":
        if absolute_path(report.get("model_path"), "model_path") != expected or "data" not in report:
            raise ValueError("Successful report has a different model or no data.")
    return report, 0 if report["status"] == "ok" else 2

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare", help="Write a complete C# source and a new run manifest.")
    p.add_argument("--job", required=True, type=Path)
    p = sub.add_parser("read", help="Read a completed report; never executes or retries a script.")
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--max-bytes", type=int, default=262144)
    sub.add_parser("list", help="List the bundled helper calls.")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result, code = prepare(args.job), 0
        elif args.command == "read":
            if not 1024 <= args.max_bytes <= 16777216:
                raise ValueError("max-bytes must be 1024..16777216.")
            result, code = read_result(args.manifest, args.max_bytes)
        else:
            result, code = {"tools": list(TOOLS)}, 0
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return code
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
