"""One bound Almond process, launched only by the shared external MCP host.

The stored attachment=cos value is a compatibility tag shared by both external routes;
it does not identify the CoS application.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.dont_write_bytecode = True
from runtime import ENGINE, WORKER_STATE_TOOL, catalog_identity, check_contract, load_catalog, validate_worker_tools
from winpipe import process_identity


def validate_external_binding(entry, args, binding, locations):
    """Validate after acquiring this generation's MCP lease, before Almond import."""
    current, _ = entry.read_binding(args.session, args.token)
    if (current != binding or current.get("attachment") != "cos"
            or current.get("storage_protocol") != 2):
        raise RuntimeError("External binding changed while the worker was acquiring its lease.")


async def configure_external_worker(mcp, args, binding, locations, runtime, catalog):
    """Use engine extension hooks and the public runtime's completion receipt."""
    if binding.get("attachment") != "cos" or binding.get("storage_protocol") != 2:
        raise RuntimeError("This entry point requires a protocol-2 external binding (attachment=cos).")
    before = [t.to_mcp_tool().model_dump(mode="json", by_alias=True, exclude_none=True)
              for t in await mcp.list_tools()]
    validate_worker_tools(catalog, before)
    identity = process_identity(os.getpid())

    @mcp.tool(name=WORKER_STATE_TOOL)
    def worker_state() -> dict:
        """Internal native completion state; never sends a Rhino request."""
        return dict(runtime.completion(), **identity)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--connection-id", required=True)
    args = parser.parse_args()
    token = os.environ.pop("ALMONDRHINO_SESSION_TOKEN")
    catalog = load_catalog()
    if os.environ.pop("ALMONDRHINO_CATALOG_ID", None) != catalog_identity(catalog):
        raise RuntimeError("Worker source/schema differs from its client snapshot. Start a new client session before connecting.")
    check_contract(catalog)
    sys.path.insert(0, str(ENGINE))
    import mcp_server as entry

    def validate(original_args, binding, locations):
        validate_external_binding(entry, original_args, binding, locations)

    async def configure(mcp, original_args, binding, locations, runtime):
        await configure_external_worker(mcp, original_args, binding, locations, runtime, catalog)

    return entry.main(["--session", args.session, "--token", token, "--port", str(args.port),
                       "--expected-version", catalog["packages"]["almond-mcp"]],
                      validate_binding=validate, configure=configure)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"[Almond external worker] {exc}", file=sys.stderr)
        raise SystemExit(1)
