"""Run the panel solver only from this checkout's editable Python package."""
from __future__ import annotations

import importlib.metadata
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from urllib.request import url2pathname


def check_source(root: Path) -> None:
    """Reject a wheel or another checkout before importing solver implementation."""
    root = root.resolve()
    source = root / "src" / "mcp"
    distributions = [dist for dist in importlib.metadata.distributions()
                     if re.sub(r"[-_.]+", "-", dist.metadata.get("Name", "")).lower() == "almond-mcp"]
    if len(distributions) != 1:
        raise RuntimeError("The solver needs exactly one editable almond-mcp installation.")
    direct = json.loads(distributions[0].read_text("direct_url.json") or "{}")
    url = urlsplit(direct.get("url", ""))
    if (direct.get("dir_info", {}).get("editable") is not True
            or url.scheme != "file" or url.netloc not in {"", "localhost"}
            or Path(url2pathname(url.path)).resolve() != root):
        raise RuntimeError("The solver's editable installation must point to its registered checkout.")
    spec = importlib.util.find_spec("almond_mcp")
    if spec is None or not spec.origin or Path(spec.origin).resolve() not in {
            source / "almond_mcp.py", source / "__init__.py"}:
        raise RuntimeError("The solver import resolves outside its registered checkout.")
    import almond_mcp
    if (Path(almond_mcp.__file__).resolve() != source / "__init__.py"
            or [Path(path).resolve() for path in almond_mcp.__path__] != [source]):
        raise RuntimeError("The solver package loaded from another source.")


def main() -> int:
    try:
        check_source(Path(__file__).resolve().parents[3])
        from almond_mcp.runtime.library_paths import configure_library_paths
        configure_library_paths()
        from almond_mcp.features.structure.structure_study import main as run
        sys.stdin.reconfigure(encoding="utf-8-sig")
        sys.stdout.reconfigure(encoding="utf-8")
        return run(sys.stdin, sys.stdout)
    except Exception as exc:
        print(json.dumps({"protocol": 1, "status": "error",
                          "message": f"Local solver startup failed: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
