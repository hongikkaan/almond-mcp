"""Compatibility alias for the Grasshopper feature parser."""
import sys

from almond_mcp.features.grasshopper import ghx_parser as implementation

sys.modules[__name__] = implementation
