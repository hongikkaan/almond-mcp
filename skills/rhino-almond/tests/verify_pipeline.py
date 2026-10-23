"""Compile and invoke each prepared source in an isolated Rhino process."""
import json
from pathlib import Path
import subprocess
import sys
import uuid

BASE = Path(__file__).resolve().parent
PROBE = BASE.parent / "scripts" / "almond_probe.py"
EXE = BASE / "bin" / "Release" / "net48" / "NativeSkillCheck.exe"
RUN = BASE / ".artifacts" / ("pipeline-" + uuid.uuid4().hex)
RUN.mkdir(parents=True)

def run(args):
    p = subprocess.run([str(x) for x in args], cwd=BASE, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if p.returncode:
        raise RuntimeError(str(args) + "\n" + p.stdout + "\n" + p.stderr)
    return p.stdout

run([EXE, "smoke", RUN / "fixture.json"])
fixture = json.loads((RUN / "fixture.json").read_text(encoding="utf-8"))
a, b, block = fixture["cube_id"], fixture["other_id"], fixture["block_id"]
requests = {
    "outline": {"ids": [block], "depth": 2, "include_geometry": True},
    "resolve-block": {"path": [block]},
    "sections": {"ids": [a, b], "axis": "Z", "stations": [5], "sample_points": 8},
    "vertical-probe": {"ids": [a, b], "xy": [[7, 5]]},
    "joint-pairs": {"pairs": [[a, b]], "compare_operations": True},
}
results = []
for tool, options in requests.items():
    job = dict(tool=tool, options=options, model_path=fixture["model_path"], artifact_dir=str(RUN))
    input_path = RUN / (tool + ".json")
    input_path.write_text(json.dumps(job), encoding="utf-8")
    manifest = json.loads(run([sys.executable, "-B", PROBE, "prepare", "--job", input_path]))
    check_path = RUN / (tool + "-native.json")
    run([EXE, "script", check_path, manifest["manifest_path"]])
    native = json.loads(check_path.read_text(encoding="utf-8"))
    result = json.loads(run([sys.executable, "-B", PROBE, "read", "--manifest", manifest["manifest_path"]]))
    assert native["compiled_and_executed"] and native["geometry_unchanged"]
    assert result["status"] == "ok" and result["run_id"] == manifest["run_id"]
    data = result["data"]
    if tool == "sections":
        assert len(data["sections"]) == 2
        assert all(row["closed_count"] == 1 and row["open_count"] == 0 for row in data["sections"])
    elif tool == "vertical-probe":
        assert all(row["intervals_known"] for row in data["rays"])
        assert abs(data["sampled_overlaps"][0]["depth"] - 10) < 1e-6
    elif tool == "joint-pairs":
        assert abs(data["pairs"][0]["overlap"]["volume_model_units3"] - 500) < 1e-6
    elif tool == "resolve-block":
        assert data["match_rule"] == "explicit_root_id" and data["editor_owner_verified"] is False
    else:
        assert block in json.dumps(data)
    row = dict(tool=tool, status="passed", source_compiled=True, native_executed=True,
               geometry_unchanged=True, result_read=True, manifest=manifest["manifest_path"])
    results.append(row)
    print(json.dumps(row), flush=True)
report = dict(status="passed", count=len(results), results=results)
(RUN / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"summary_path": str(RUN / "summary.json"), "passed": len(results)}), flush=True)
