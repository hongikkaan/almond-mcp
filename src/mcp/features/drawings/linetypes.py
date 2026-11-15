"""Read the checkout's linetype profiles without changing any asset-library location."""
from copy import deepcopy
import json
import math
from pathlib import Path


PROFILE_FILE = Path(__file__).resolve().parents[2] / "profiles/linetype/manifest.json"


def _segments(value):
    if not isinstance(value, list) or not value:
        raise ValueError("Linetype segments must be a non-empty array.")
    for segment in value:
        if not isinstance(segment, dict):
            raise ValueError("Each linetype segment must be an object.")
        length = segment.get("length")
        if (type(length) not in (int, float) or not math.isfinite(length) or length <= 0
                or type(segment.get("is_solid")) is not bool):
            raise ValueError("Linetype segments need positive finite lengths and boolean is_solid.")
    if not any(segment["is_solid"] for segment in value):
        raise ValueError("A linetype needs at least one solid segment.")
    return value


def style_layers(recipe):
    """Resolve profiles; retain explicit legacy definitions for other custom names."""
    profile = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    if not isinstance(profile, dict) or type(profile.get("schema_version")) is not int or profile["schema_version"] != 1:
        raise ValueError("Unsupported linetype profile schema_version.")
    if not isinstance(profile.get("linetypes"), list) or not isinstance(profile.get("legacy_name_rules"), list):
        raise ValueError("Linetype profiles and legacy name rules must be arrays.")
    definitions = {}
    for definition in profile["linetypes"]:
        if not isinstance(definition, dict):
            raise ValueError("Each linetype profile must be an object.")
        name = definition["name"]
        if not isinstance(name, str) or not name.strip() or name.strip().casefold() in definitions:
            raise ValueError("Linetype profile names must be non-empty and unique.")
        definitions[name.strip().casefold()] = _segments(definition["segments"])
    fallback = _segments(profile["legacy_default_segments"])
    rules = profile["legacy_name_rules"]
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("contains"), str) or not rule["contains"]:
            raise ValueError("Linetype name rules need a non-empty contains string.")
        _segments(rule["segments"])
    layers = deepcopy(recipe.get("layers", []))
    if not isinstance(layers, list) or not layers:
        raise ValueError("Drawing recipe must contain at least one layer.")
    for layer in layers:
        if not isinstance(layer, dict):
            raise ValueError("Each drawing layer must be an object.")
        name = layer.get("linetype") or "Continuous"
        if not isinstance(name, str):
            raise ValueError("Drawing layer linetype names must be strings.")
        name = name.strip() or "Continuous"
        if name.casefold() in {"continuous", "bylayer", "byparent"}:
            continue
        # Existing AppData A4 recipes still contain inline copies. The shared
        # profile must own registered names without rewriting those user files.
        segments = definitions.get(name.casefold())
        if segments is None:
            segments = layer.get("linetype_segments")
        if segments is None:
            segments = next((rule["segments"] for rule in rules
                             if rule["contains"].casefold() in name.casefold()), fallback)
        layer["linetype_segments"] = deepcopy(_segments(segments))
    return layers
