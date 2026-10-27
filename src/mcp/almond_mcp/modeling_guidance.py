"""Versioned, package-local modeling guidance; no server, model or store imports."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re


PACKAGE = Path(__file__).resolve().parent
BUNDLE = PACKAGE / "modeling_guides"


def _read_content(path: Path) -> bytes:
    raw = path.read_bytes()
    if path.suffix != ".png":
        raw = raw.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")
    return raw


def content_digest(path: Path) -> str:
    return hashlib.sha256(_read_content(path)).hexdigest()


def source_files() -> list[Path]:
    """All shipped guide files, including additions, participate in session identity."""
    return sorted(path for path in BUNDLE.rglob("*") if path.is_file())


@lru_cache(maxsize=1)
def _snapshot() -> dict:
    manifest = json.loads((BUNDLE / "manifest.json").read_text(encoding="utf-8"))
    version = manifest.pop("guide_version")
    encoded = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if manifest.get("format") != 1 or hashlib.sha256(encoded).hexdigest() != version:
        raise ValueError("Modeling guide manifest is inconsistent; install a matching package.")
    files = {}
    for name, expected in manifest["files"].items():
        if not re.fullmatch(r"(?:[a-z][a-z0-9-]*\.md|assets/[a-z][a-z0-9-]*\.png)", name):
            raise ValueError("Invalid modeling guide package path.")
        path = BUNDLE / name
        raw = _read_content(path)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"Modeling guide {name} changed; install a matching package and start a new session.")
        files[name] = raw if name.endswith(".png") else raw.decode("utf-8")
    instructions = {}
    for key, filename in (("startup", "FUNDAMENTAL-INSTRUCTIONS.md"),
                          ("model_context", "MODEL-CONTEXT-INSTRUCTIONS.md")):
        raw = _read_content(PACKAGE / filename)
        if hashlib.sha256(raw).hexdigest() != manifest[f"{key}_sha256"]:
            raise ValueError(f"Modeling {key} guidance changed; rebuild the guide bundle and start a new session.")
        instructions[key] = raw.decode("utf-8").strip()
    return {**manifest, "guide_version": version, "content": files, **instructions}


def startup_instructions() -> str:
    return _snapshot()["startup"]


def project_instructions() -> str:
    snapshot = _snapshot()
    return snapshot["startup"] + "\n\n" + snapshot["model_context"]


def tool_guidance(name: str) -> str:
    return _snapshot()["tool_hints"].get(name, "")


def read_guide(topic: str = "index", include_images: bool = False) -> tuple[dict, list[bytes]]:
    """Return a bounded allowlisted topic and optional original images from one snapshot."""
    snapshot = _snapshot()
    result = {"status": "success", "guide_version": snapshot["guide_version"], "topic_id": topic}
    if topic == "index":
        result["topics"] = [{key: item[key] for key in ("id", "title", "when_to_read")}
                            for item in snapshot["topics"]]
        return result, []
    entry = next((item for item in snapshot["topics"] if item["id"] == topic), None)
    if entry is None:
        raise ValueError("Unknown modeling guide topic. Call get_modeling_guide(topic='index') for available topics.")
    result.update({key: deepcopy(entry[key]) for key in ("title", "related_tools", "source_refs")})
    result["text"] = snapshot["content"][entry["file"]]
    result["images_available"] = deepcopy(entry["images"])
    images = [snapshot["content"][item["file"]] for item in entry["images"]] if include_images else []
    result["images_included"] = len(images)
    return result, images
