"""Record or verify the prebuilt Rhino runtime committed with its source."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "src/rhp/runtime-manifest.json"
BUNDLES = ("src/rhp/RhinoAlmondBridge/plugin-runtime", "src/rhp/AlmondCOS/plugin-runtime")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_digest(path):
    data = path.read_bytes()
    if path.suffix.lower() != ".ico":
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def verify(root, manifest):
    errors = []
    for group in ("sources", "files"):
        for relative, expected in manifest[group].items():
            path = root / relative
            checksum = source_digest if group == "sources" else digest
            if not path.is_file() or checksum(path) != expected:
                errors.append(relative)
    return errors


def record(root):
    tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")
    sources = [p for p in tracked if (
        p.startswith(("src/rhp/", "src/engine/native/"))
        and (Path(p).suffix.lower() in (".cs", ".csproj", ".props", ".targets", ".ico", ".resx")
             or Path(p).name in ("NuGet.Config", "packages.lock.json")
             or p.startswith("src/rhp/Asset_Panel/web/")))
        or p == "src/mcp/almond_mcp/modeling_policy.json"]
    files = sorted(p.relative_to(root).as_posix() for bundle in BUNDLES
                   for p in (root / bundle).rglob("*") if p.is_file())
    required = [f"{BUNDLES[0]}/RhinoAlmondBridge.rhp", f"{BUNDLES[1]}/AlmondCOS.rhp"]
    if not all(p in files for p in required):
        raise RuntimeError("Build both committed runtime bundles before recording their hashes.")
    if digest(root / BUNDLES[0] / "Almond.Engine.dll") != digest(root / BUNDLES[1] / "Almond.Engine.dll"):
        raise RuntimeError("Bridge and COS must ship the same Engine binary.")
    return {"format": 1, "sources": {p: source_digest(root / p) for p in sorted(sources)},
            "files": {p: digest(root / p) for p in files}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true", help="Maintainer: record completed builds before committing.")
    args = parser.parse_args()
    path = ROOT / MANIFEST
    if args.record:
        path.write_text(json.dumps(record(ROOT), indent=2) + "\n", encoding="utf-8")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    errors = verify(ROOT, manifest)
    if errors:
        raise SystemExit("Runtime differs from its recorded source/build; rebuild and commit it:\n" + "\n".join(errors))
    print(f"Runtime verified: {len(manifest['sources'])} source files, {len(manifest['files'])} runtime files.")


if __name__ == "__main__":
    main()
