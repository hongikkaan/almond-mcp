"""Assemble Almond feature factories, shared services, and the TCP entry point.

Feature implementations live under features/. Public imports and helper exports
remain available here for runtime rebinding and existing callers.
"""
import os
import base64
import io
import json
import math
import socket
import struct
import hashlib
import re
import sys
import tempfile
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from almond_mcp.library_index import AssetLibraryIndexer
from fastmcp import FastMCP
from fastmcp.resources import ResourceContent, ResourceResult
from fastmcp.tools import ToolResult
from mcp.types import ImageContent, TextContent
from PIL import Image as PillowImage
from pydantic import StrictFloat, StrictInt
from almond_mcp.features.grasshopper.ghx_parser import GHParser, validate_capsule_manifest
from almond_mcp.retrieval_store import AlmondStore, ComponentReconciliationError, DrawingSheetReconciliationError
from almond_mcp.features.modeling import modeling_policy, modeling_setup
from almond_mcp.features.assets import drawing_assets
from almond_mcp import asset_passport, paths
from almond_mcp.features.structure import asset_loads, native_structure, structure_study, design_codes
from almond_mcp.features.capture import conditioning
from almond_mcp.features.exchange import exchange
from almond_mcp.features.assets import drafting

from almond_mcp.features.guidance.library import ConstructionLibrary, HistoryLibrary

from almond_mcp.features.modeling.library import MaterialLibrary

from almond_mcp.features.grasshopper.library import LibraryIndexer, _sync_capsule_library
from almond_mcp.features.grasshopper.tools import _CAPSULE_GEOMETRY_TYPES

from almond_mcp.features.structure.tools import KARAMBA_ONLY_TYPES

from almond_mcp.features.drawings.library import DrawingRecipeIndexer

# ── Constants ────────────────────────────────────────────────────────────────

DELIMITER = b'\n<<EOF>>\n'
LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_LIBRARY_DIR")
DRAWING_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_DRAWING_ASSET_DIR")
DIAGRAM_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_DIAGRAM_ASSET_DIR")
GENERATED_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_GENERATED_ASSET_DIR")
DRAWING_RECIPE_DIR = paths.resolve_dir("RHINO_MCP_DRAWING_RECIPE_DIR")
DRAFTING_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_DRAFTING_DIR")
CAPSULE_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_CAPSULE_DIR")
MATERIAL_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_MATERIAL_DIR")
CONSTRUCTION_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_CONSTRUCTION_DIR")
STATE_DB_PATH = paths.resolve_state_db()
BRIDGE_HOST = '127.0.0.1'
BRIDGE_PORT = 5000
CHESTNUT_URL = os.environ.get(
    "CHESTNUT_URL",
    "https://chestnut-mnvo.onrender.com",
).rstrip("/")
print(f"Chestnut publish target: {CHESTNUT_URL}", file=sys.stderr)

# ── MCP Server ───────────────────────────────────────────────────────────────

mcp = FastMCP("Almond")


# Build index once on startup
indexer = LibraryIndexer(LIBRARY_DIR)
drawing_asset_indexer = AssetLibraryIndexer(
    DRAWING_LIBRARY_DIR,
    library_id="drawing_assets",
    label="drawing",
)
diagram_asset_indexer = AssetLibraryIndexer(
    DIAGRAM_LIBRARY_DIR,
    library_id="diagram_assets",
    label="diagram",
)
generated_asset_indexer = AssetLibraryIndexer(
    GENERATED_LIBRARY_DIR,
    library_id="generated_assets",
    label="generated",
)
drawing_recipe_indexer = DrawingRecipeIndexer(DRAWING_RECIPE_DIR)


material_library = MaterialLibrary(MATERIAL_LIBRARY_DIR)
construction_library = ConstructionLibrary(CONSTRUCTION_LIBRARY_DIR)
history_library = HistoryLibrary(paths.resolve_dir("RHINO_MCP_HISTORY_DIR"))
retrieval_store = AlmondStore(STATE_DB_PATH)
retrieval_store.sync_assets(
    list(drawing_asset_indexer.assets.values()),
    library_id="drawing_assets",
)
# Retire the legacy supplier catalogue from searchable cache; local files and
# scene history are retained.
retrieval_store.sync_assets([], library_id="ikea")
retrieval_store.sync_assets(
    list(diagram_asset_indexer.assets.values()),
    library_id="diagram_assets",
)
retrieval_store.sync_assets(
    list(generated_asset_indexer.assets.values()),
    library_id="generated_assets",
)


capsule_sync_report = _sync_capsule_library(retrieval_store, CAPSULE_LIBRARY_DIR)

# ── TCP Helpers ──────────────────────────────────────────────────────────────

def _send_and_receive(payload_bytes: bytes, timeout: float = 60.0) -> str:
    """Send payload to the Rhino bridge using a length-prefix protocol and receive response."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((BRIDGE_HOST, BRIDGE_PORT))

        # Length-prefix: send 4-byte big-endian length header, then data
        length = len(payload_bytes)
        s.sendall(length.to_bytes(4, 'big'))
        s.sendall(payload_bytes)

        # Receive: read 4-byte length header, then exact data
        header = b''
        while len(header) < 4:
            chunk = s.recv(4 - len(header))
            if not chunk:
                raise ConnectionError("Bridge closed connection while reading response header.")
            header += chunk

        resp_length = int.from_bytes(header, 'big')
        resp_data = b''
        while len(resp_data) < resp_length:
            chunk = s.recv(min(16384, resp_length - len(resp_data)))
            if not chunk:
                raise ConnectionError("Bridge closed connection while reading response body.")
            resp_data += chunk

        return resp_data.decode('utf-8')
    finally:
        s.close()




_VIEW_ENGINE: str | None = None   # which engine drew the current overlay ("native" | "api")


# Feature factories: explicit composition, no runtime directory discovery.
from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.assets.tools import register as _register_assets
from almond_mcp.features.capture.tools import register as _register_capture
from almond_mcp.features.components.tools import register as _register_components
from almond_mcp.features.context.tools import register as _register_context
from almond_mcp.features.diagrams.tools import register as _register_diagrams
from almond_mcp.features.drawings.tools import register as _register_drawings
from almond_mcp.features.egress.tools import register as _register_egress
from almond_mcp.features.exchange.tools import register as _register_exchange
from almond_mcp.features.grasshopper.tools import register as _register_grasshopper
from almond_mcp.features.guidance.tools import register as _register_guidance
from almond_mcp.features.modeling.tools import register as _register_modeling
from almond_mcp.features.placement.tools import register as _register_placement
from almond_mcp.features.planning.tools import register as _register_planning
from almond_mcp.features.publishing.tools import register as _register_publishing
from almond_mcp.features.scenes.tools import register as _register_scenes
from almond_mcp.features.structure.tools import register as _register_structure

_feature_context = FeatureContext(globals())
globals().update(_register_assets(mcp, _feature_context))
globals().update(_register_capture(mcp, _feature_context))
globals().update(_register_components(mcp, _feature_context))
globals().update(_register_context(mcp, _feature_context))
globals().update(_register_diagrams(mcp, _feature_context))
globals().update(_register_drawings(mcp, _feature_context))
globals().update(_register_egress(mcp, _feature_context))
globals().update(_register_exchange(mcp, _feature_context))
globals().update(_register_grasshopper(mcp, _feature_context))
globals().update(_register_guidance(mcp, _feature_context))
globals().update(_register_modeling(mcp, _feature_context))
globals().update(_register_placement(mcp, _feature_context))
globals().update(_register_planning(mcp, _feature_context))
globals().update(_register_publishing(mcp, _feature_context))
globals().update(_register_scenes(mcp, _feature_context))
globals().update(_register_structure(mcp, _feature_context))
# End feature composition.

if __name__ == "__main__":
    mcp.run()
