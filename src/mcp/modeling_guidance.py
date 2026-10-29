"""Read canonical package guidance directly; no generated copy or model imports."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

PACKAGE = Path(__file__).resolve().parent
BUNDLE = PACKAGE / "features/guidance/guides"
BASIC_GUIDE = PACKAGE / "BASIC-INSTRUCTIONS.md"


def _read_content(path: Path) -> bytes:
    raw = path.read_bytes()
    return raw if path.suffix == ".png" else raw.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")


def content_digest(path: Path) -> str:
    return hashlib.sha256(_read_content(path)).hexdigest()


def source_files() -> list[Path]:
    return sorted([*(p for p in BUNDLE.rglob("*") if p.is_file()), BASIC_GUIDE])


def _section(text: str, heading: str, children: bool = True) -> str:
    lines = text.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines)
               if re.sub(r"%%.*?%%", "", line).rstrip() == heading]
    if len(matches) != 1:
        raise ValueError(f"Missing or duplicate guide heading: {heading}")
    start = matches[0]
    level = len(heading) - len(heading.lstrip("#"))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        match = re.match(r"^(#{1,6}) ", lines[i])
        if match and (not children or len(match[1]) <= level):
            end = i
            break
    return "".join(lines[start:end]).strip()


@lru_cache(maxsize=1)
def _snapshot() -> dict:
    inventory = source_files()
    raw = {p: _read_content(p) for p in inventory}
    mapping = json.loads(raw[BUNDLE / "mcp-guide-map.json"])
    topics, content, hints = [], {}, {}

    def source(path: Path) -> str:
        return raw[path].decode("utf-8")

    def reference(path: Path, heading: str = "") -> dict:
        return {"path": "src/mcp/" + path.relative_to(PACKAGE).as_posix(),
                "heading": heading, "sha256": hashlib.sha256(raw[path]).hexdigest()}

    for item in mapping["topics"]:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", item["id"]) or item["id"] in ("index", "basic"):
            raise ValueError("Invalid/reserved guide topic ID")
        texts, refs, images = [], [], []
        for ref in item["sections"]:
            path = BASIC_GUIDE if ref["path"] == BASIC_GUIDE.name else (BUNDLE / ref["path"]).resolve()
            if path != BASIC_GUIDE:
                path.relative_to(BUNDLE)
            texts.append(_section(source(path), ref["heading"], ref.get("children", True)))
            refs.append(reference(path, ref["heading"]))
        text = "\n\n".join(texts) + "\n"
        for before, after in mapping["link_replacements"].items():
            text = text.replace(before, after)
        for image in item.get("images", []):
            path = (BUNDLE / image["path"]).resolve()
            path.relative_to(BUNDLE)
            name = path.relative_to(BUNDLE).as_posix()
            content[name] = raw[path]
            images.append({"file": name, "alt": image["alt"], "sha256": hashlib.sha256(raw[path]).hexdigest()})
        filename = item["id"] + ".md"
        if filename in content:
            raise ValueError("Duplicate guide topic")
        content[filename] = text
        topics.append({key: item[key] for key in ("id", "title", "summary", "when_to_read", "related_tools")} |
                      {"file": filename, "source_refs": refs, "images": images})
        for name in item.get("hint_tools", []):
            hints[name] = (hints.get(name, "") + f'\nWhen {item["trigger"]}, read get_modeling_guide(topic="{item["id"]}") '
                           "if not already read for the current guide_version or the rule is unclear.").strip()
    content[BASIC_GUIDE.name] = source(BASIC_GUIDE).strip()
    topics.append({"id": "basic", "title": "Basic instructions", "summary": "Basic Rhino Almond guidance",
                   "when_to_read": "At first use", "related_tools": ["get_modeling_guide"],
                   "file": BASIC_GUIDE.name, "source_refs": [reference(BASIC_GUIDE)], "images": []})
    if inventory != source_files() or any(_read_content(p) != value for p, value in raw.items()):
        raise RuntimeError("Guide source changed while reading; start a new session.")
    identity = {p.relative_to(PACKAGE).as_posix(): hashlib.sha256(value).hexdigest() for p, value in raw.items()}
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {"topics": topics, "content": content, "tool_hints": hints, "guide_version": version,
            "basic": content[BASIC_GUIDE.name]}


def startup_instructions() -> str:
    snapshot = _snapshot()
    return ('Almond inspects and edits Rhino architecture and drawings. On first use, call '
            'get_modeling_guide(topic="basic") to read BASIC-INSTRUCTIONS.md. '
            f'guide_version={snapshot["guide_version"]}')


def project_instructions() -> str:
    snapshot = _snapshot()
    return snapshot["basic"]


def tool_guidance(name: str) -> str:
    return _snapshot()["tool_hints"].get(name, "")


def read_guide(topic: str = "index", include_images: bool = False) -> tuple[dict, list[bytes]]:
    snapshot = _snapshot()
    result = {"status": "success", "guide_version": snapshot["guide_version"], "topic_id": topic}
    if topic == "index":
        result["topics"] = [{key: item[key] for key in ("id", "title", "summary", "when_to_read")}
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
