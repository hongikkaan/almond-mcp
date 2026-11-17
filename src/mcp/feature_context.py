"""Explicit dependencies owned by one assembled MCP application."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from almond_mcp.features.assets.library_index import AssetLibraryIndexer
    from almond_mcp.features.drawings.library import DrawingRecipeIndexer
    from almond_mcp.features.exchange.tools import ExchangeReports
    from almond_mcp.features.grasshopper.library import LibraryIndexer
    from almond_mcp.features.guidance.library import ConstructionLibrary, HistoryLibrary
    from almond_mcp.features.modeling.library import MaterialLibrary
    from almond_mcp.retrieval_store import AlmondStore


@dataclass(frozen=True)
class FeatureContext:
    _send_and_receive: Callable[..., str]
    retrieval_store: AlmondStore
    LIBRARY_DIR: str
    DRAWING_LIBRARY_DIR: str
    GENERATED_LIBRARY_DIR: str
    DRAFTING_LIBRARY_DIR: str
    CAPSULE_LIBRARY_DIR: str
    indexer: LibraryIndexer
    drawing_asset_indexer: AssetLibraryIndexer
    diagram_asset_indexer: AssetLibraryIndexer
    generated_asset_indexer: AssetLibraryIndexer
    drawing_recipe_indexer: DrawingRecipeIndexer
    material_library: MaterialLibrary
    construction_library: ConstructionLibrary
    history_library: HistoryLibrary
    exchange_reports: Callable[[], ExchangeReports]
    _execute_rhinocode: Callable[..., dict] | None = None
