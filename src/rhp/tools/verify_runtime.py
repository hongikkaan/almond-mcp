"""Record/verify each owner's runtime; verify shared Engine agreement at integration."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
MANIFESTS = {
    "bridge": "src/rhp/RhinoAlmondBridge/runtime-manifest.json",
    "cos": "src/cos/runtime-manifest.json",
}
BUNDLES = ("src/rhp/RhinoAlmondBridge/plugin-runtime", "src/rhp/AlmondRhino/plugin-runtime")
COMPONENT_BUNDLES = dict(zip(MANIFESTS, BUNDLES))
SOURCE_ROOTS = {
    "bridge": ("src/rhp/RhinoAlmondBridge/", "src/rhp/Structural_Analysis/",
               "src/rhp/Asset_Panel/", "src/rhp/RhinoTerminal/", "src/rhp/Engine/",
               "src/mcp/rhino/", "src/mcp/features/context/native/",
               "src/mcp/features/components/native/", "src/mcp/features/modeling/native/",
               "src/mcp/features/assets/native/", "src/mcp/features/drawings/native/",
               "src/mcp/features/grasshopper/native/", "src/mcp/features/exchange/native/",
               "src/mcp/features/structure/native/"),
    "cos": ("src/cos/rhp/", "src/rhp/Engine/"),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_digest(path):
    data = path.read_bytes()
    if path.suffix.lower() != ".ico":
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def is_source(relative, component):
    path = Path(relative)
    if any(part in {"tests", "data", "bin", "obj"} or part.startswith("plugin-")
           for part in path.parts):
        return False
    if relative == "global.json":
        return True
    if component == "bridge" and relative == "src/mcp/modeling_policy.json":
        return True
    return relative.startswith(SOURCE_ROOTS[component]) and (
        path.suffix.lower() in {".cs", ".csproj", ".props", ".targets", ".ico", ".resx"}
        or path.name in {"NuGet.Config", "packages.lock.json"}
        or relative.startswith(("src/rhp/Asset_Panel/web/", "src/rhp/RhinoTerminal/src/web/")))


def source_files(root, component):
    tracked = subprocess.check_output([
        "git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"
    ]).decode().split("\0")
    return sorted({p for p in tracked if (root / p).is_file() and is_source(p, component)})


def verify(root, manifest):
    errors = []
    for group in ("sources", "files"):
        for relative, expected in manifest[group].items():
            path = root / relative
            checksum = source_digest if group == "sources" else digest
            if not path.is_file() or checksum(path) != expected:
                errors.append(relative)
    return errors


def record(root, component):
    bundle = COMPONENT_BUNDLES[component]
    files = sorted(p.relative_to(root).as_posix() for p in (root / bundle).rglob("*") if p.is_file())
    entry = "RhinoAlmondBridge.rhp" if component == "bridge" else "AlmondRhino.rhp"
    required = [f"{bundle}/{entry}", f"{bundle}/Almond.Engine.dll"]
    if component == "bridge":
        required += [f"{bundle}/{name}" for name in (
            "LICENSE", "THIRD-PARTY-NOTICES.md", "archive/THIRD-PARTY-NOTICES.md",
            "archive/ATTRIBUTION.txt", "archive/ui/vendor/LICENSE", "archive/ui/vendor/THIRD-PARTY-LICENSES.txt",
            *(f"licenses/{name}-LICENSE.txt" for name in ("Porta.Pty", "Vanara", "addon-fit", "xterm")),
        )]
    if not all(p in files for p in required):
        raise RuntimeError("Runtime bundles are missing executables or required license notices.")
    return {"format": 1, "component": component,
            "sources": {p: source_digest(root / p) for p in source_files(root, component)},
            "files": {p: digest(root / p) for p in files}}


def verify_engine_pair(root):
    if digest(root / BUNDLES[0] / "Almond.Engine.dll") != digest(root / BUNDLES[1] / "Almond.Engine.dll"):
        raise RuntimeError("Bridge and AlmondRhino must ship the same Engine binary. Build both after an Engine change.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true", help="Record completed builds before committing.")
    parser.add_argument("--component", choices=("all", *MANIFESTS), default="all")
    args = parser.parse_args()
    selected = list(MANIFESTS) if args.component == "all" else [args.component]
    if args.component == "all":
        verify_engine_pair(ROOT)
    for component in selected:
        path = ROOT / MANIFESTS[component]
        if args.record:
            path.write_text(json.dumps(record(ROOT, component), indent=2) + "\n", encoding="utf-8")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("component") != component:
            raise SystemExit(f"Wrong runtime manifest owner: {path}")
        errors = verify(ROOT, manifest)
        if sorted(manifest["sources"]) != source_files(ROOT, component):
            errors.append("Source inventory changed; rebuild and record this component.")
        if errors:
            raise SystemExit(f"{component} runtime differs from its source/build:\n" + "\n".join(errors))
        print(f"{component}: {len(manifest['sources'])} source files, {len(manifest['files'])} runtime files verified.")


if __name__ == "__main__":
    main()
