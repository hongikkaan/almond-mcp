"""Curated material manifest loading and filtering."""
import json
import sys
from pathlib import Path

from almond_mcp import paths
from almond_mcp.features.modeling import modeling_policy


def _installed_layer_defaults(directory: Path) -> dict:
    """Read styles for unchanged copies of previously shipped AppData records."""
    name = paths.LIBRARY_DIRS["RHINO_MCP_MATERIAL_DIR"]
    default_dirs = {paths.user_data_dir() / name}
    if sys.platform == "win32":
        default_dirs.add(Path.home() / "AppData" / "Local" / paths.APP_NAME / name)
    if directory.resolve() not in default_dirs:
        return {}
    bundled = Path(__file__).resolve().parents[2] / "profiles/material/manifest.json"
    try:
        records = json.loads(bundled.read_text(encoding="utf-8"))["materials"]
        return {record["material_id"]: record for record in records}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Bundled material layer settings unavailable: {exc}", file=sys.stderr)
        return {}


class MaterialLibrary:
    """Curated PBR material definitions (src/mcp/profiles/material/manifest.json)."""

    REQUIRED = ("material_id", "name", "category", "base_color",
                "metallic", "roughness", "opacity", "ue_material_slot")

    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.materials: dict[str, dict] = {}
        manifest_path = self.directory / "manifest.json"
        if not manifest_path.is_file():
            print(f"Material manifest missing: {manifest_path}", file=sys.stderr)
            return
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"Material manifest unreadable: {exc}", file=sys.stderr)
            return
        defaults = _installed_layer_defaults(self.directory)
        for material in manifest.get("materials", []):
            try:
                if isinstance(material, dict) and "layer_settings" not in material:
                    bundled = defaults.get(material.get("material_id"))
                    if bundled and material == {k: v for k, v in bundled.items() if k != "layer_settings"}:
                        material = bundled
                material = modeling_policy.validate_material(material)
            except (KeyError, TypeError, ValueError) as exc:
                print(f"Skipped invalid material: {exc}", file=sys.stderr)
                continue
            self.materials[material["material_id"]] = material
        print(f"Indexed {len(self.materials)} PBR materials.", file=sys.stderr)

    def get(self, material_id: str) -> dict | None:
        return self.materials.get(material_id)

    def list(self, category: str = "", query: str = "") -> list[dict]:
        needle = query.strip().lower()
        results = []
        for material in self.materials.values():
            if category and material["category"] != category:
                continue
            if needle:
                haystack = " ".join([
                    material["material_id"], material["name"],
                    material.get("description", ""),
                    " ".join(material.get("tags", [])),
                ]).lower()
                if needle not in haystack:
                    continue
            results.append(material)
        return results
