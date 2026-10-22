"""Audit a Yak release without installing it or modifying Rhino."""
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "mcp"))
from almond_mcp import __version__

RUNTIME = {"RhinoAlmondBridge.rhp", "Almond.Engine.dll", "Microsoft.CodeAnalysis.CSharp.dll",
           "Microsoft.CodeAnalysis.dll", "Newtonsoft.Json.dll", "Porta.Pty.dll",
           "Vanara.Core.dll", "Vanara.PInvoke.Kernel32.dll", "Vanara.PInvoke.Shared.dll"}
TERMINAL_LICENSES = {f"licenses/{name}-LICENSE.txt" for name in ("Porta.Pty", "Vanara", "addon-fit", "xterm")}
RUNTIME_METADATA = {"RhinoAlmondBridge.deps.json", "RhinoAlmondBridge.runtimeconfig.json"}


def verify(path, rhino_sdk_version=None):
    version = ET.parse(ROOT/"src/rhp/RhinoAlmondBridge/RhinoAlmondBridge.csproj").findtext("PropertyGroup/Version")
    tag = re.fullmatch(rf"almondbridge-{re.escape(version)}-rh(8_\d+)-win\.yak", path.name)
    if tag is None or (rhino_sdk_version is not None and tag[1] != rhino_sdk_version.replace(".", "_")):
        raise ValueError("Incorrect Yak version or Rhino/platform compatibility tag")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate zip members")
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts or "\\" in name:
                raise ValueError(f"Unsafe member: {name}")
            if p.suffix.lower() in {".rhp", ".dll"} and name not in RUNTIME:
                raise ValueError(f"Unexpected executable: {name}")
            if p.suffix.lower() in {".skp", ".3dm", ".gh", ".ghx", ".gha", ".sqlite3", ".exe", ".py", ".ps1"}:
                raise ValueError(f"Forbidden member: {name}")
            if "/files/drawing/" in name or "/raw/" in name:
                raise ValueError(f"Community or raw model included: {name}")
        for name in RUNTIME | TERMINAL_LICENSES | RUNTIME_METADATA | {"manifest.yml", "LICENSE", "THIRD-PARTY-NOTICES.md", "GETTING-STARTED.md", "archive/ATTRIBUTION.txt", "archive/ui/vendor/LICENSE", "archive/ui/vendor/THIRD-PARTY-LICENSES.txt"}:
            if name not in names:
                raise ValueError(f"Missing package file: {name}")
        manifest = archive.read("manifest.yml").decode("utf-8-sig")
        if f"version: {version}" not in manifest or "name: almondbridge" not in manifest:
            raise ValueError("Yak manifest version/name mismatch")
        bundle = json.loads(archive.read("archive/bundle.json"))
        if bundle["version"] != __version__:
            raise ValueError("Python/archive version mismatch")
        for route, record in bundle["routes"].items():
            member = "archive/" + record["path"]
            if ".." in PurePosixPath(record["path"]).parts or record["path"].startswith("/"):
                raise ValueError("Unsafe route target")
            if hashlib.sha256(archive.read(member)).hexdigest() != record["sha256"]:
                raise ValueError(f"Checksum mismatch: {route}")
        catalogue = json.loads(archive.read("archive/api/catalogue.json"))
        counts = catalogue["counts"]
        if counts != {"assets":57,"models":50,"elements":7,"drawing_packages":10,"views":60}:
            raise ValueError(f"Unexpected catalogue: {counts}")
        glbs = [n for n in names if n.endswith(".glb")]
        if len(glbs) != 50 or any(not n.startswith("archive/files/generated/models/") for n in glbs):
            raise ValueError("Generated-model pack is incomplete")
        evidence = json.loads(archive.read("archive/evidence/source-register.json"))
        sources = {a["asset_id"]:a for a in evidence["assets"]}
        for record in catalogue["assets"]:
            if record["kind"] == "element":
                if record["available"] or record["model"] or record["preview"]:
                    raise ValueError("Community model exposed by distributed catalogue")
                continue
            model = archive.read("archive/" + bundle["routes"][record["model"]]["path"])
            if hashlib.sha256(model).hexdigest().upper() != sources[record["id"]]["model_sha256"]:
                raise ValueError("Source evidence does not match bundled model")
            captured = sources[record["id"]]["recorded_generation"].get("captured_generation")
            if captured:
                image_path = "archive/" + bundle["routes"][record["generation_image"]]["path"]
                if hashlib.sha256(archive.read(image_path)).hexdigest() != captured["image"]["output_sha256"]:
                    raise ValueError("Captured generation image is missing or changed")
            if record["drawing"]:
                drawing_path = "archive/" + bundle["routes"][record["drawing"]["record"]]["path"]
                drawing = json.loads(archive.read(drawing_path))
                for filename, expected in drawing["files"].items():
                    if PurePosixPath(filename).name != filename:
                        raise ValueError("Unsafe drawing member")
                    payload = archive.read(str(PurePosixPath(drawing_path).parent / filename))
                    if hashlib.sha256(payload).hexdigest().upper() != expected:
                        raise ValueError("Drawing package is stale or incomplete")
    return {"status":"success", "yak":path.name,"bridge_version":version,"archive_version":__version__,
            "rhino_sdk_tag":"rh" + tag[1], "target_framework":"net8.0-windows",
            "counts":counts,"routes_checked":len(bundle["routes"]),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_mb":round(path.stat().st_size/1e6,2), "rhino_in_process_smoke":"pending"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package",type=Path)
    parser.add_argument("--report",type=Path)
    parser.add_argument("--rhino-sdk-version",help="Expected referenced Rhino SDK major.minor, e.g. 8.34")
    args=parser.parse_args()
    report=verify(args.package, args.rhino_sdk_version)
    if args.report: args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
