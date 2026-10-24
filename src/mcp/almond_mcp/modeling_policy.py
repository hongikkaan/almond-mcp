"""Shared metadata names and MCP modeling rules; loading creates no Rhino state."""
from __future__ import annotations

import json
import math
from pathlib import Path


POLICY = json.loads(Path(__file__).with_name("modeling_policy.json").read_text(encoding="utf-8"))


def key(name: str) -> str:
    for mapping in ("public_object_keys", "internal_object_keys", "group_keys"):
        if name in POLICY[mapping]:
            return POLICY[mapping][name]
    raise KeyError(name)


def validate_layer_path(path: str) -> str:
    if not isinstance(path, str):
        raise ValueError("layer path must be a string")
    parts = path.split("::")
    if (parts[0] != POLICY["construction_layer_root"]
            or any(not part or part != part.strip() or any(
                ord(c) < 32 or c == ':' for c in part) for part in parts)):
        raise ValueError("layer path must contain valid nonempty names beneath M")
    return path


def validate_material(material: dict) -> dict:
    if not isinstance(material, dict):
        raise ValueError("material must be an object")
    for field in ("material_id", "name", "category", "ue_material_slot"):
        if not isinstance(material.get(field), str) or not material[field].strip():
            raise ValueError(f"material {field} must be a nonempty string")
    rgb = material.get("base_color")
    if not isinstance(rgb, list) or len(rgb) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in rgb):
        raise ValueError("material base_color must contain three integers in 0..255")
    for field in ("metallic", "roughness", "opacity"):
        value = material.get(field)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"material {field} must be finite and in 0..1")
    return {key: value for key, value in material.items() if key != "layer_path"}
