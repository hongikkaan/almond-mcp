"""External Almond MCP launcher for the editable checkout.

Example (Windows, outside Rhino):
  Normally started by the single top-level start button through codex.ps1.

The loopback endpoint is selected ONLY in this Python process's memory.
Models in one directory share scene.sqlite3 and tmp. Connection metadata is separate.
The launcher uses internal module names, not an upstream-supported port option.
The existing sender wrapper adds connection/request identity in this process only.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path
from project import (ExclusiveFile, SharedStorageLease, STORAGE_PROTOCOL,
                     process_start_ticks, read_binding, read_json, verify_process, write_json)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True,
                        help="Extra Rhino bridge port, e.g. 5501 through 5510")
    parser.add_argument("--state-db", type=Path,
                        help="Must match the selected model's .almond database")
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--expected-version", help="Require this exact installed almond-mcp version")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535 or args.port == 5000:
        parser.error("Choose an unused port from 1024 to 65535, excluding 5000.")
    return args


def main(argv: list[str] | None = None, *, validate_binding=None, configure=None) -> int:
    args = parse_args(argv)
    if args.expected_version is not None:
        installed = version("almond-mcp")
        if installed != args.expected_version:
            raise RuntimeError(f"Package version mismatch: expected {args.expected_version}, got {installed}.")
    binding, locations = read_binding(args.session, args.token)
    if binding.get('storage_protocol') != STORAGE_PROTOCOL:
        raise RuntimeError('This Rhino uses the previous storage protocol. Load the new host and reconnect before sharing a DB.')
    verify_process(binding)
    if binding['port'] != args.port:
        raise RuntimeError('Port and selected project disagree.')
    db = Path(locations['state_db'])
    if args.state_db is not None and args.state_db.resolve() != db:
        raise RuntimeError('Do not connect this model to another project database.')
    with SharedStorageLease(locations['storage']), ExclusiveFile(Path(locations['session_dir']) / 'mcp.lock'):
        current, _ = read_binding(args.session, args.token)
        if current != binding:
            raise RuntimeError('Connection changed while the worker was starting.')
        if validate_binding is not None:
            validate_binding(args, binding, locations)
        worker_path = Path(locations['session_dir']) / 'worker.json'
        worker = dict(schema='almond-worker', storage_protocol=STORAGE_PROTOCOL, token=args.token,
                      pid=os.getpid(), process_start_ticks=process_start_ticks(os.getpid()))
        write_json(worker_path, worker)
        return serve(args, binding, locations, db, configure=configure)


async def configure_project_context(mcp, args, binding, locations):
    """Publish the bound output path before the model writes any Rhino script."""
    from fastmcp.server.transforms.tool_transform import ToolTransform
    from fastmcp.tools.tool_transform import ToolTransformConfig

    script_tool = await mcp.get_tool('execute_rhino_script')
    if script_tool is None:
        raise RuntimeError('Almond execute_rhino_script is unavailable.')
    artifact_dir = locations['call_root']
    csharp_dir = '@"' + artifact_dir.replace('"', '""') + '"'
    guidance = (
        'CURRENT ALMOND PROJECT AND FILE OUTPUTS\n'
        f"Saved model: {locations['model_path']}\n"
        f"Working directory: {locations['project_dir']}\n"
        f"Scene database: {locations['state_db']}\n"
        'The DB is shared by saved models in this directory. Use explicit scene IDs.\n'
        f'Project artifact directory: {artifact_dir}\n'
        'Before the first Rhino action, call almond_project_info to check this binding. '
        'Save task-local inventories, screenshots, diagnostic reports and temporary code '
        'under the returned artifact_dir, using an explicit absolute path in both the '
        'Rhino script and subsequent shell/image reads. '
        f'C# example: System.IO.Path.Combine({csharp_dir}, "review.txt"). '
        'Create a unique task subdirectory there before writing. Public report, export '
        'and conditioning output arguments use a fresh call subdirectory when empty. '
        'C# executes inside Rhino, whose existing process TEMP is separate from the '
        'Codex/Python MCP TEMP. Path.GetTempPath(), relative paths, and hardcoded '
        'AppData/Windows Temp paths do not select this project artifact directory. '
        'An existing global scratch folder is not a reason to reuse it; if the project '
        'directory is not writable, report the error instead of falling back elsewhere. '
        'Explicit user input/export locations take precedence. Do not relocate existing '
        'files or save the Rhino model merely to set an output path.'
    )
    mcp.instructions = ((mcp.instructions or '') + '\n\n' + guidance).strip()
    # Metadata only: preserve the original tool's signature and execution body.
    mcp.add_transform(ToolTransform({'execute_rhino_script': ToolTransformConfig(
        description=((script_tool.description or '') + '\n\n' + guidance).strip())}))

    @mcp.tool()
    def almond_project_info() -> dict:
        """Read the bound model, DB and artifact_dir before the first Rhino action.

        Use artifact_dir as the explicit absolute base for task-local reports,
        screenshots and temporary code, including C# executed inside Rhino and
        shell/image reads. mcp_temp/effective_temp belong to Python; Rhino's original
        TEMP (rhino_temp_at_attach) may differ and is not the project output path.
        This is binding metadata, not a live active-document check. For a terminal
        connection, use /exit, switch the saved document, then almond to reconnect.
        """
        current, _ = read_binding(args.session, args.token)
        if current != binding:
            raise RuntimeError('Connection changed. Exit Codex and reconnect with almond.')
        verify_process(current)
        actual_temp = tempfile.gettempdir()
        return dict(**locations, slot=binding['label'], port=binding['port'], pid=binding['pid'],
                    artifact_dir=artifact_dir, effective_temp=actual_temp, mcp_temp=actual_temp,
                    rhino_temp_at_attach=binding.get('rhino_temp'),
                    working_directory=os.getcwd(), python_executable=sys.executable,
                    attachment=binding.get('attachment', 'external'), live_document_checked=False,
                    storage_protocol=STORAGE_PROTOCOL, storage_scope='model_directory',
                    output_rule='Use artifact_dir explicitly in Rhino C# and shell file paths; '
                                'do not infer it from Rhino TEMP or an old global scratch folder.')


def serve(args, binding, locations, db, *, configure=None):
    # No import-time SQLite access occurs before the project lease is acquired.
    for variable in ('TEMP', 'TMP', 'TMPDIR'):
        os.environ[variable] = locations['temp']
    tempfile.tempdir = None
    os.chdir(locations['project_dir'])

    # Must be set BEFORE server.py imports and creates its scene store.
    os.environ["RHINO_MCP_STATE_DB"] = str(db)

    from shared_store import ProjectRuntime, StoreGate
    # SQLite's initialization, reindex transactions and closing checkpoints must
    # not race a second worker. The original store and library resolver are used.
    with StoreGate(locations['storage']):
        from library_paths import configure_library_paths
        configure_library_paths()
        from almond_mcp import paths
        library_dirs = {variable: str(paths.resolve_dir(variable)) for variable in paths.LIBRARY_DIRS}
        from almond_mcp import server
    worker_path = Path(locations['session_dir']) / 'worker.json'
    worker = read_json(worker_path)
    worker['library_dirs'] = library_dirs
    write_json(worker_path, worker)

    # Fail rather than silently falling back to the wrong Rhino on port 5000
    # if an upstream update has changed the expected transport helper.
    sender = getattr(server, "_send_and_receive", None)
    code = getattr(sender, "__code__", None)
    if (not hasattr(server, "BRIDGE_HOST") or
            not hasattr(server, "BRIDGE_PORT") or code is None or
            "BRIDGE_HOST" not in code.co_names or
            "BRIDGE_PORT" not in code.co_names):
        raise RuntimeError(
            "Unsupported Almond transport implementation. "
            "No MCP service has been started. Recheck the installed package source.")

    server.BRIDGE_HOST = "127.0.0.1"
    server.BRIDGE_PORT = args.port
    runtime = ProjectRuntime(args, binding, locations)
    original_sender = server._send_and_receive

    def bound_sender(payload_bytes, *positional, **keywords):
        return runtime.send(original_sender, payload_bytes, *positional, **keywords)

    # Retain the existing process-local sender wrapper. The installed function's
    # socket/framing implementation is called unchanged with an owned envelope.
    server._send_and_receive = bound_sender
    from compat_almond import install
    install(server, runtime)
    server.mcp.add_middleware(runtime)

    async def prepare():
        await configure_project_context(server.mcp, args, binding, locations)
        if configure is not None:
            await configure(server.mcp, args, binding, locations, runtime)

    asyncio.run(prepare())
    print("[AlmondParallel] Rhino target: {0}:{1}".format(
        server.BRIDGE_HOST, args.port), file=sys.stderr)
    print("[AlmondParallel] Scene DB: {0}".format(db), file=sys.stderr)
    # Use the same MCP entry point as Almond's own cmd_serve.
    # stdout is reserved for the MCP protocol.
    print("[AlmondParallel] This is NOT a read-only service. Almond C# queries can create default layers.", file=sys.stderr)
    server.mcp.run()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print("[AlmondParallel] Startup/runtime error: {0}".format(exc), file=sys.stderr)
        raise SystemExit(1)
