"""Canonical standard D recipe and its public layer-path choices."""
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field


_RECIPE_FILE = Path(__file__).resolve().parents[2] / "profiles" / "drawing" / "standard_d.json"
STANDARD_D = json.loads(_RECIPE_FILE.read_text(encoding="utf-8"))
STANDARD_D_ID = STANDARD_D["recipe_id"]
STANDARD_D_LAYERS = {layer["path"]: layer for layer in STANDARD_D["layers"]}
_Choices = Literal[tuple(STANDARD_D_LAYERS)]
StandardDLayerPath = Annotated[_Choices | None, Field(description="; ".join(
    f"{path}: {layer['role']}" for path, layer in STANDARD_D_LAYERS.items()
))]
