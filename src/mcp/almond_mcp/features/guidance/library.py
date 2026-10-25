"""Curated construction systems and architectural typology libraries."""

import json
import sys
from pathlib import Path


class ConstructionLibrary:
    """Curated construction-system guidance (asset/constructions/Constructionfiles/manifest.json).

    Parameters distilled from Ching, Building Construction Illustrated
    (4th ed.): span ranges, depth rules of thumb, member spacing, and
    assembly notes per construction system, keyed to validate_structure's
    structure_type/material vocabulary and to asset/constructions/Materialfiles material_ids."""

    REQUIRED = ("system_id", "name", "category", "structural_material",
                "structure_types", "span_range_m")

    # validate_structure accepts S355 as a steel grade; guidance treats it as Steel.
    MATERIAL_ALIASES = {"s355": "Steel", "steel": "Steel", "concrete": "Concrete",
                        "wood": "Wood", "timber": "Wood", "aluminium": "Aluminium",
                        "aluminum": "Aluminium"}

    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.systems: dict[str, dict] = {}
        self.reference: dict = {}
        self.source = ""
        manifest_path = self.directory / "manifest.json"
        if not manifest_path.is_file():
            print(f"Construction manifest missing: {manifest_path}", file=sys.stderr)
            return
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"Construction manifest unreadable: {exc}", file=sys.stderr)
            return
        self.reference = manifest.get("reference", {})
        self.source = manifest.get("source", "")
        for system in manifest.get("systems", []):
            if not all(key in system for key in self.REQUIRED):
                continue
            self.systems[system["system_id"]] = system
        print(f"Indexed {len(self.systems)} construction systems.", file=sys.stderr)

    def get(self, system_id: str) -> dict | None:
        return self.systems.get(system_id)

    def normalize_material(self, material: str) -> str:
        return self.MATERIAL_ALIASES.get(material.strip().lower(), material.strip())

    def list(self, category: str = "", query: str = "", material: str = "",
             structure_type: str = "") -> list[dict]:
        needle = query.strip().lower()
        wanted_material = self.normalize_material(material) if material else ""
        wanted_type = structure_type.strip().lower()
        results = []
        for system in self.systems.values():
            if category and system["category"] != category:
                continue
            if wanted_material and system["structural_material"] != wanted_material:
                continue
            if wanted_type and wanted_type not in system["structure_types"]:
                continue
            if needle:
                haystack = " ".join([
                    system["system_id"], system["name"], system["category"],
                    system.get("structural_material", ""),
                    " ".join(system.get("tags", [])),
                    " ".join(note for note in system.get("construction_notes", [])),
                    " ".join(element.get("role", "") + " " + element.get("note", "")
                             for element in system.get("elements", [])),
                ]).lower()
                if needle not in haystack:
                    continue
            results.append(system)
        return results

    def assess_span(self, structure_type: str, material: str,
                    span_m: float | None) -> dict:
        """Constructibility cross-check for a validate_structure run: which
        curated systems cover this structure_type/material, does the span sit
        inside a real system's range, and what member depth would it imply."""
        wanted_material = self.normalize_material(material)
        wanted_type = structure_type.strip().lower()
        candidates = [s for s in self.systems.values()
                      if wanted_type in s["structure_types"]
                      and s["structural_material"] == wanted_material]
        check: dict = {
            "source": "Ching, Building Construction Illustrated (4th ed.) - preliminary sizing guidance",
            "matching_systems": [],
            "warnings": [],
        }
        if not candidates:
            check["warnings"].append(
                f"No curated construction system covers structure_type "
                f"'{structure_type}' in {wanted_material}; span plausibility "
                f"not assessed.")
            return check
        span_known = span_m is not None and span_m > 0
        fitting = []
        for system in candidates:
            lo, hi = system["span_range_m"]
            entry = {
                "system_id": system["system_id"],
                "name": system["name"],
                "span_range_m": [lo, hi],
                "bci_ref": system.get("bci_ref", []),
            }
            if span_known and hi > 0:
                entry["fits_span"] = bool(lo <= span_m <= hi)
                depths = []
                for rule in system.get("depth_rules", []):
                    ratio = rule.get("span_ratio", 0)
                    if ratio:
                        depths.append({
                            "element": rule["element"],
                            "suggested_depth_mm": round(span_m * 1000 / ratio),
                            "rule": f"span/{ratio}",
                        })
                if depths:
                    entry["depth_guidance"] = depths
                if entry["fits_span"]:
                    fitting.append(system)
            check["matching_systems"].append(entry)
        if span_known and not fitting:
            spans = ", ".join(
                f"{s['system_id']} ({s['span_range_m'][0]}-{s['span_range_m'][1]} m)"
                for s in candidates if s["span_range_m"][1] > 0)
            check["warnings"].append(
                f"Span {span_m:g} m is outside the typical range of every "
                f"curated {wanted_material} system for '{structure_type}': "
                f"{spans}. The structure may still solve numerically, but as "
                f"drawn it does not correspond to a standard construction "
                f"system - consider a different system, material, or "
                f"intermediate supports.")
        return check


class HistoryLibrary:
    """Curated architectural typology narratives (asset/history/Historyfiles/manifest.json).

    Distilled from Ching, Jarzombek & Prakash, A Global History of
    Architecture. NARRATION ONLY: entries feed project storytelling and
    typology context; they never drive geometry, sizing, or structural
    decisions - those belong to the construction library."""

    REQUIRED = ("typology_id", "name", "era", "narrative", "gha_ref")

    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.entries: dict[str, dict] = {}
        self.source = ""
        manifest_path = self.directory / "manifest.json"
        if not manifest_path.is_file():
            print(f"History manifest missing: {manifest_path}", file=sys.stderr)
            return
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"History manifest unreadable: {exc}", file=sys.stderr)
            return
        self.source = manifest.get("source", "")
        for entry in manifest.get("entries", []):
            if not all(key in entry for key in self.REQUIRED):
                continue
            self.entries[entry["typology_id"]] = entry
        print(f"Indexed {len(self.entries)} typology narratives.", file=sys.stderr)

    def get(self, typology_id: str) -> dict | None:
        return self.entries.get(typology_id)

    def list(self, query: str = "", construction_system: str = "",
             structure_type: str = "") -> list[dict]:
        needle = query.strip().lower()
        wanted_type = structure_type.strip().lower()
        results = []
        for entry in self.entries.values():
            if construction_system and construction_system not in \
                    entry.get("related_construction_systems", []):
                continue
            if wanted_type and wanted_type not in entry.get("structure_types", []):
                continue
            if needle:
                haystack = " ".join([
                    entry["typology_id"], entry["name"], entry["era"],
                    entry.get("region", ""), entry["narrative"],
                    entry.get("urban_role", ""),
                    " ".join(entry.get("tags", [])),
                    " ".join(p.get("name", "") + " " + p.get("place", "")
                             for p in entry.get("precedents", [])),
                ]).lower()
                if needle not in haystack:
                    continue
            results.append(entry)
        return results
