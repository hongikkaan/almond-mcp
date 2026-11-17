"""Open backing stores and assemble a server on explicit startup."""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Callable, Mapping, TYPE_CHECKING

from fastmcp import FastMCP

from almond_mcp import paths
from almond_mcp.bridge_transport import BridgeTransport
from almond_mcp.feature_context import FeatureContext

if TYPE_CHECKING:
    from almond_mcp.features.exchange.tools import ExchangeReports


@dataclass(frozen=True)
class ServerApplication:
    mcp: FastMCP
    features: FeatureContext


def create_server(
    *,
    state_db: str | Path,
    library_dirs: Mapping[str, str],
    send: Callable[..., str],
    execute_source: Callable[..., dict] | None = None,
    exchange_reports: Callable[[], ExchangeReports] | None = None,
) -> ServerApplication:
    from almond_mcp.features.assets.library_index import AssetLibraryIndexer
    from almond_mcp.features.drawings.library import DrawingRecipeIndexer
    from almond_mcp.features.exchange.tools import local_exchange_reports
    from almond_mcp.features.grasshopper.library import LibraryIndexer, _sync_capsule_library
    from almond_mcp.features.guidance.library import ConstructionLibrary, HistoryLibrary
    from almond_mcp.features.modeling.library import MaterialLibrary
    from almond_mcp.retrieval_store import AlmondStore
    from almond_mcp.tool_declarations import FEATURE_MODULES

    drawing = library_dirs["RHINO_MCP_DRAWING_ASSET_DIR"]
    diagram = library_dirs["RHINO_MCP_DIAGRAM_ASSET_DIR"]
    generated = library_dirs["RHINO_MCP_GENERATED_ASSET_DIR"]
    grasshopper = library_dirs["RHINO_MCP_LIBRARY_DIR"]
    capsules = library_dirs["RHINO_MCP_CAPSULE_DIR"]
    indexer = LibraryIndexer(grasshopper)
    drawing_assets = AssetLibraryIndexer(drawing, "drawing_assets", "drawing")
    diagram_assets = AssetLibraryIndexer(diagram, "diagram_assets", "diagram")
    generated_assets = AssetLibraryIndexer(generated, "generated_assets", "generated")
    shared_ids = diagram_assets.assets.keys() & generated_assets.assets.keys()
    if shared_ids:
        raise ValueError(f"Asset ID collision between diagram_assets and generated_assets: {', '.join(sorted(shared_ids))}.")
    drawing_recipes = DrawingRecipeIndexer(library_dirs["RHINO_MCP_DRAWING_RECIPE_DIR"])
    materials = MaterialLibrary(library_dirs["RHINO_MCP_MATERIAL_DIR"])
    construction = ConstructionLibrary(library_dirs["RHINO_MCP_CONSTRUCTION_DIR"])
    history = HistoryLibrary(library_dirs["RHINO_MCP_HISTORY_DIR"])
    features = FeatureContext(
        _send_and_receive=send,
        retrieval_store=AlmondStore(state_db),
        LIBRARY_DIR=grasshopper,
        DRAWING_LIBRARY_DIR=drawing,
        GENERATED_LIBRARY_DIR=generated,
        DRAFTING_LIBRARY_DIR=library_dirs["RHINO_MCP_DRAFTING_DIR"],
        CAPSULE_LIBRARY_DIR=capsules,
        indexer=indexer,
        drawing_asset_indexer=drawing_assets,
        diagram_asset_indexer=diagram_assets,
        generated_asset_indexer=generated_assets,
        drawing_recipe_indexer=drawing_recipes,
        material_library=materials,
        construction_library=construction,
        history_library=history,
        _execute_rhinocode=execute_source,
        exchange_reports=exchange_reports or local_exchange_reports,
    )
    # Retire the legacy supplier catalogue from searchable cache. Keep its
    # local files and scene history, as in the standalone and bound launchers.
    features.retrieval_store.sync_asset_libraries({
        "ikea": [],
        diagram_assets.library_id: list(diagram_assets.assets.values()),
        generated_assets.library_id: list(generated_assets.assets.values()),
    })
    _sync_capsule_library(features.retrieval_store, capsules)

    mcp = FastMCP("Almond")
    for module in FEATURE_MODULES:
        import_module(module).register(mcp, features)
    return ServerApplication(mcp, features)


def serve_standalone() -> int:
    library_dirs = {variable: paths.resolve_dir(variable) for variable in paths.LIBRARY_DIRS}
    application = create_server(
        state_db=paths.resolve_state_db(),
        library_dirs=library_dirs,
        send=BridgeTransport("127.0.0.1", 5000),
    )
    application.mcp.run()
    return 0
