"""Compatibility alias for the feature-owned drawing_assets implementation."""

import sys

from almond_mcp.features.assets import drawing_assets as implementation

sys.modules[__name__] = implementation
