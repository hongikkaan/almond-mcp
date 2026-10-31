"""Shared manifest indexing for drawing, diagram, and generated assets."""
import json
import re
import sys
from pathlib import Path


class AssetLibraryIndexer:
    """Indexes one controlled asset manifest and resolves safe local files."""

    def __init__(self, directory: str, library_id: str, label: str):
        self.directory = Path(directory).resolve()
        self.manifest_path = self.directory / "manifest.json"
        self.library_id = library_id
        self.label = label
        self.assets: dict[str, dict] = {}
        self.catalogue_region = ""
        self.catalogue_checked = ""
        self._load()

    def _load(self):
        if not self.manifest_path.is_file():
            print(f"{self.label} manifest not found: {self.manifest_path}", file=sys.stderr)
            return

        with self.manifest_path.open("r", encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)

        self.catalogue_region = manifest.get("catalogue_region", "")
        self.catalogue_checked = manifest.get("catalogue_checked", "")
        manifest_library_id = manifest.get("library_id", self.library_id)
        if manifest_library_id != self.library_id:
            print(
                f"Skipping {self.label}: expected library_id {self.library_id}, "
                f"found {manifest_library_id}.",
                file=sys.stderr,
            )
            return
        # Treat each successful manifest read as a complete snapshot. Updating
        # the old map in place would keep removed IDs searchable after reload.
        assets: dict[str, dict] = {}
        for asset in manifest.get("assets", []):
            asset_id = str(asset.get("asset_id", "")).strip()
            relative_file = str(asset.get("file", "")).strip()
            if not asset_id or not relative_file:
                continue
            resolved_file = (self.directory / relative_file).resolve()
            try:
                resolved_file.relative_to(self.directory)
            except ValueError:
                print(f"Skipping {self.label} asset outside library root: {asset_id}", file=sys.stderr)
                continue
            record = dict(asset)
            record["library_id"] = self.library_id
            record["_resolved_file"] = str(resolved_file)
            record["file_available"] = resolved_file.is_file()
            assets[asset_id] = record

        self.assets = assets
        print(f"Indexed {len(self.assets)} {self.label} assets.", file=sys.stderr)

    def public_record(self, asset: dict) -> dict:
        return {key: value for key, value in asset.items() if not key.startswith("_")}

    def get(self, asset_id: str) -> dict | None:
        return self.assets.get(asset_id)

    def search(
        self,
        query: str = "",
        category: str = "",
        max_width_mm: float = 0,
        max_depth_mm: float = 0,
        max_height_mm: float = 0,
        exact_dimensions_only: bool = False,
        limit: int = 10,
        _all: bool = False,
    ) -> list[dict]:
        query_tokens = set(re.findall(r"[^\W_]+", query.casefold(), re.UNICODE))
        category = category.lower().strip()
        results = []

        for asset in self.assets.values():
            if category and asset.get("category", "").lower() != category:
                continue
            if exact_dimensions_only and asset.get("match_status") != "exact_dimensions":
                continue

            dimensions = asset.get("dimensions_mm", {})
            if max_width_mm > 0 and dimensions.get("width", 0) > max_width_mm:
                continue
            if max_depth_mm > 0 and dimensions.get("depth", 0) > max_depth_mm:
                continue
            if max_height_mm > 0 and dimensions.get("height", 0) > max_height_mm:
                continue

            searchable = " ".join([
                asset.get("name", ""),
                asset.get("description", ""),
                asset.get("series", ""),
                asset.get("product", ""),
                asset.get("variant", ""),
                asset.get("category", ""),
                " ".join(asset.get("tags", [])),
            ]).lower()
            score = sum(1 for token in query_tokens if token in searchable)
            if query_tokens and score == 0:
                continue
            results.append((score, asset.get("series", ""), self.public_record(asset)))

        results.sort(key=lambda item: (-item[0], item[1], item[2]["asset_id"]))
        return [item[2] for item in (results if _all else results[:max(1, min(limit, 50))])]

    def search_page(self, *, limit: int = 20, offset: int = 0, **filters) -> dict:
        """Manifest-only paging; no project DB registration or refresh is needed."""
        if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
            raise ValueError("limit must be 1-100 and offset must be a nonnegative integer.")
        matches = self.search(**filters, _all=True)
        page = matches[offset:offset + limit]
        return {"assets": page, "total": len(matches), "limit": limit, "offset": offset,
                "truncated": offset + len(page) < len(matches)}
