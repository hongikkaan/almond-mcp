"""Shared metadata names and MCP modeling rules; loading creates no Rhino state."""
from __future__ import annotations

import json
import math
from pathlib import Path


POLICY = json.loads((Path(__file__).resolve().parents[2] / "modeling_policy.json").read_text(encoding="utf-8"))


def key(name: str) -> str:
    for mapping in ("public_object_keys", "internal_object_keys"):
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


def material_layer(material: dict) -> dict:
    """Resolve the one managed layer and the optional first-creation styles."""
    root = POLICY["construction_layer_root"]
    category, material_id = material["category"], material["material_id"]
    default_path = validate_layer_path(f"{root}::{category}::{material_id}")
    if len(default_path.split("::")) != 3:
        raise ValueError("material category and material_id must each be a single layer name")
    settings = material.get("layer_settings", {})
    if not isinstance(settings, dict) or set(settings) - {
        "path", "color", "plot_color", "plot_weight_mm", "linetype"
    }:
        raise ValueError("invalid material layer_settings")
    path = validate_layer_path(settings.get("path", default_path))
    if len(path.split("::")) != 3 or path.split("::")[1] != category:
        raise ValueError("material layer must be beneath its material category")
    for field in ("color", "plot_color"):
        if field in settings:
            rgb = settings[field]
            if not isinstance(rgb, list) or len(rgb) != 3 or any(
                type(v) is not int or not 0 <= v <= 255 for v in rgb
            ):
                raise ValueError(f"material layer {field} requires three integers in 0..255")
    if "plot_weight_mm" in settings:
        weight = settings["plot_weight_mm"]
        if type(weight) not in (int, float) or not math.isfinite(weight) or weight < 0:
            raise ValueError("material layer plot_weight_mm must be finite and nonnegative")
    if "linetype" in settings:
        name = settings["linetype"]
        if not isinstance(name, str) or not name or name != name.strip():
            raise ValueError("material layer linetype must be a nonempty name")
    return {**settings, "path": path}
