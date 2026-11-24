"""Controlled drawing-style recipe index."""
import json
import re
import sys
from pathlib import Path

from almond_mcp.features.drawings.standard import STANDARD_D, STANDARD_D_ID, STANDARD_D_LAYERS


_RESERVED_D_PATHS = {path.casefold() for path in STANDARD_D_LAYERS} | {"d", "d::plansection"}


class DrawingRecipeIndexer:
    """Loads audited drawing-style recipes from a controlled directory."""

    def __init__(self, directory: str):
        self.directory = Path(directory).resolve()
        self.recipes: dict[str, dict] = {}
        if not self.directory.is_dir():
            print(f"Drawing recipe directory not found: {self.directory}", file=sys.stderr)
            return
        for recipe_path in sorted(self.directory.glob("*.json")):
            try:
                recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
                recipe_id = str(recipe.get("recipe_id", "")).strip()
                if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", recipe_id):
                    raise ValueError("invalid recipe_id")
                layers = recipe.get("layers")
                if isinstance(layers, list):
                    for layer in layers:
                        if isinstance(layer, dict):
                            layer.pop("linetype_segments", None)
                if recipe.get("layer_template") == STANDARD_D_ID:
                    recipe["_layer_template"] = recipe.pop("layer_template")
                    if not isinstance(layers, list):
                        raise ValueError("Recipe layers must be a list")
                    for layer in layers:
                        path = layer["path"].casefold()
                        if path in _RESERVED_D_PATHS or path.startswith("d::plansection::"):
                            raise ValueError(f"Reserved drawing layer: {layer['path']}")
                    recipe["layers"] = [*layers, *STANDARD_D["layers"]]
                recipe["_source_file"] = str(recipe_path)
                self.recipes[recipe_id] = recipe
            except Exception as exc:
                print(f"Skipping drawing recipe {recipe_path.name}: {exc}", file=sys.stderr)
        print(f"Indexed {len(self.recipes)} drawing recipes.", file=sys.stderr)

    def get(self, recipe_id: str) -> dict | None:
        return self.recipes.get(recipe_id)

    @staticmethod
    def public_record(recipe: dict) -> dict:
        return {key: value for key, value in recipe.items() if not key.startswith("_")}
