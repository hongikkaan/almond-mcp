"""Standalone Almond MCP entry point."""
from almond_mcp.store_common import (
    ComponentReconciliationError as ComponentReconciliationError,
    DrawingSheetReconciliationError as DrawingSheetReconciliationError,
)


def serve_standalone() -> int:
    from almond_mcp import paths
    from almond_mcp.bridge_transport import BridgeTransport
    from almond_mcp.startup import create_server

    library_dirs = {variable: paths.resolve_dir(variable) for variable in paths.LIBRARY_DIRS}
    application = create_server(
        state_db=paths.resolve_state_db(),
        library_dirs=library_dirs,
        send=BridgeTransport("127.0.0.1", 5000),
    )
    application.mcp.run()
    return 0


class _StandaloneEntry:
    def run(self):
        serve_standalone()


mcp = _StandaloneEntry()


if __name__ == "__main__":
    raise SystemExit(serve_standalone())
