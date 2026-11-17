"""Standalone Almond MCP entry point."""
from almond_mcp.store_common import (
    ComponentReconciliationError as ComponentReconciliationError,
    DrawingSheetReconciliationError as DrawingSheetReconciliationError,
)


def serve_standalone() -> int:
    from almond_mcp.startup import serve_standalone as serve

    return serve()


class _StandaloneEntry:
    def run(self):
        serve_standalone()


mcp = _StandaloneEntry()


if __name__ == "__main__":
    raise SystemExit(serve_standalone())
