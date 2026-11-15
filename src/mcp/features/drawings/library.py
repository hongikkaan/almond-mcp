"""Controlled drawing-style recipe index."""
import json
import re
import sys
from threading import RLock
from pathlib import Path


class DrawingRecipeIndexer:
    """Loads audited drawing-style recipes from a controlled directory."""

    def __init__(self, directory: str):
        self.directory = Path(directory).resolve()
        self.recipes: dict[str, dict] = {}
        self._lock = RLock()
        try:
            self.refresh()
        except ValueError as exc:
            print(str(exc), file=sys.stderr)

    def refresh(self) -> dict[str, dict]:
        """Publish a complete snapshot; a partial/invalid edit retains the last good index."""
        with self._lock:
            return self._refresh()

    def _refresh(self) -> dict[str, dict]:
        if not self.directory.is_dir():
            raise ValueError(f"Drawing recipe directory not found: {self.directory}")
        recipes = {}
        for recipe_path in sorted(self.directory.glob("*.json")):
            # This existing authoring template is deliberately not an executable recipe.
            if recipe_path.name.lower() == "sample.json":
                continue
            try:
                recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
                if not isinstance(recipe, dict):
                    raise ValueError("recipe must be a JSON object")
                if recipe.get("is_sample") is True:
                    continue
                recipe_id = str(recipe.get("recipe_id", "")).strip()
                if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", recipe_id):
                    raise ValueError("invalid recipe_id")
                if recipe_id in recipes:
                    raise ValueError(f"duplicate recipe_id: {recipe_id}")
                recipe["recipe_id"] = recipe_id
                recipe["_source_file"] = str(recipe_path)
                recipes[recipe_id] = recipe
            except Exception as exc:
                raise ValueError(f"Drawing recipe refresh failed at {recipe_path.name}: {exc}") from exc
        self.recipes = recipes
        return recipes

    def get(self, recipe_id: str) -> dict | None:
        return self.refresh().get(recipe_id)

    @staticmethod
    def public_record(recipe: dict) -> dict:
        return {key: value for key, value in recipe.items() if not key.startswith("_")}
