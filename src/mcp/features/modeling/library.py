"""Curated material manifest loading and filtering."""
import json
import sys
from pathlib import Path

from almond_mcp.features.modeling import modeling_policy


class MaterialLibrary:
    """Curated PBR material definitions (asset/constructions/Materialfiles/manifest.json)."""

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
        for material in manifest.get("materials", []):
            try:
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
