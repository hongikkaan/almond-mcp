"""Build/check the modeling guidance bundle without importing the server."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
SOURCES = ROOT / "docs/modeling/guidance"
PACKAGE = ROOT / "src/mcp/almond_mcp"
BUNDLE = PACKAGE / "modeling_guides"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_source(path: Path) -> bytes:
    raw = path.read_bytes()
    return raw if path.suffix == ".png" else raw.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")


def section(text: str, heading: str, *, children: bool = True) -> str:
    lines = text.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if line.rstrip() == heading]
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


def build() -> dict[str, bytes]:
    snapshot = {}

    def source(path: Path) -> bytes:
        path = path.resolve()
        if path not in snapshot:
            snapshot[path] = read_source(path)
        return snapshot[path]

    mapping = json.loads(source(SOURCES / "mcp-guide-map.json"))
    output, sources, topics, hints = {}, {}, [], {}
    for item in mapping["topics"]:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", item["id"]) or item["id"] == "index":
            raise ValueError("Invalid/reserved guide topic ID")
        texts, refs = [], []
        for ref in item["sections"]:
            path = SOURCES / ref["path"]
            path.resolve().relative_to(SOURCES.resolve())
            text = source(path).decode("utf-8")
            sources[ref["path"]] = digest(text.encode("utf-8"))
            texts.append(section(text, ref["heading"], children=ref.get("children", True)))
            refs.append({"path": path.relative_to(ROOT).as_posix(), "heading": ref["heading"],
                         "sha256": sources[ref["path"]]})
        text = "\n\n".join(texts) + "\n"
        # Repository links/images are not accessible through an installed MCP client.
        for before, after in mapping["link_replacements"].items():
            text = text.replace(before, after)
        filename = item["id"] + ".md"
        if filename in output:
            raise ValueError("Duplicate guide topic")
        output[filename] = text.encode("utf-8")
        images = []
        for image in item.get("images", []):
            image_path = SOURCES / image["path"]
            image_path.resolve().relative_to(SOURCES.resolve())
            raw = source(image_path)
            target = "assets/" + image_path.name
            output[target] = raw
            images.append({"file": target, "alt": image["alt"], "sha256": digest(raw)})
        topics.append({key: item[key] for key in ("id", "title", "summary", "when_to_read", "related_tools")} |
                      {"file": filename, "source_refs": refs, "images": images})
        for name in item.get("hint_tools", []):
            sentence = (f"When {item['trigger']}, read get_modeling_guide(topic=\"{item['id']}\") "
                        "if not already read for the current guide_version or the rule is unclear.")
            hints[name] = (hints.get(name, "") + "\n" + sentence).strip()
    manifest = {"format": 1, "topics": topics, "tool_hints": hints,
                "files": {name: digest(raw) for name, raw in sorted(output.items())},
                "startup_sha256": digest(source(PACKAGE / "FUNDAMENTAL-INSTRUCTIONS.md")),
                "model_context_sha256": digest(source(PACKAGE / "MODEL-CONTEXT-INSTRUCTIONS.md")),
                "source_files": sources,
                "excluded_sections": mapping["excluded_sections"]}
    encoded = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["guide_version"] = digest(encoded)
    output["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    for path, original in snapshot.items():
        if read_source(path) != original:
            raise RuntimeError(f"Guide source changed during generation: {path.name}. Rebuild before publishing.")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    existing = {path.relative_to(BUNDLE).as_posix(): path for path in BUNDLE.rglob("*") if path.is_file()}
    stale = sorted(set(existing) - set(expected))
    if stale:
        raise ValueError(f"Remove explicitly reviewed obsolete bundle files: {stale}")
    changed = []
    for name, raw in expected.items():
        path = BUNDLE / name
        actual = path.read_bytes() if path.exists() else None
        if actual is not None and not name.endswith(".png"):
            actual = actual.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")
        if actual == raw:
            continue
        changed.append(name)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    if args.check and changed:
        print("Stale modeling guide bundle: " + ", ".join(changed), file=sys.stderr)
        return 1
    print(f"Modeling guide bundle {'verified' if args.check else 'built'}: {len(expected)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
