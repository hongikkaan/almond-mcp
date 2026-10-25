"""Compatibility alias for the feature-owned asset_repository implementation."""

import sys

from almond_mcp.features.assets import asset_repository as implementation

sys.modules[__name__] = implementation
