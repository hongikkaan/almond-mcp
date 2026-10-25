"""Compatibility alias for the Grasshopper feature parser."""
import sys

from almond_mcp.features.grasshopper import ghx_parser as implementation

if __name__ == "__main__":
    implementation.main()
else:
    sys.modules[__name__] = implementation
