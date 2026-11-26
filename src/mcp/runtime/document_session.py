"""Run the MCP server for one checkout-bound Rhino document."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from project import (
    ExclusiveFile, SharedStorageLease, STORAGE_PROTOCOL, process_start_ticks, read_binding, read_json,
    verify_process, write_json,
)


def run_document_session(args, *, register_tools, validate_binding=None, configure=None) -> int:
    """Keep the document lease until the worker has recorded its close."""
    binding, locations = read_binding(args.session, args.token)
    if binding.get('storage_protocol') != STORAGE_PROTOCOL:
        raise RuntimeError('This Rhino uses the previous storage protocol. Load the new host and reconnect before sharing a DB.')
    verify_process(binding)
    if binding['port'] != args.port:
        raise RuntimeError('Port and selected project disagree.')
    db = Path(locations['state_db'])
    if args.state_db is not None and args.state_db.resolve() != db:
        raise RuntimeError('Do not connect this model to another project database.')
    try:
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
            try:
                return _serve(args, binding, locations, db, register_tools=register_tools, configure=configure)
            finally:
                worker["closed"] = True
                write_json(worker_path, worker)
    finally:
        from shared_store import StoreGate
        from storage_cleanup import cleanup_retired_sessions
        with StoreGate(locations["storage"]):
            cleanup_retired_sessions(Path(locations["storage"]))


def _exchange_reports(runtime):
    from almond_mcp.features.exchange.tools import ExchangeReports
    from storage_cleanup import plain_descendant

    batch = runtime.scope.get()
    if batch is None or batch.sealed:
        raise RuntimeError("No active operation for Almond asset helper reports.")
    # send() creates this directory only after admitting the capability request.
    # The report helper may use the owned directory, but cannot create it.
    directory = Path(runtime.locations["call_root"]) / batch.operation_id
    return ExchangeReports(plain_descendant(directory, Path(runtime.locations["temp"])), managed=True)


def _serve(args, binding, locations, db, *, register_tools, configure):
    from almond_mcp.bridge_transport import BridgeTransport
    from almond_mcp.startup import create_server
    from library_paths import bound_library_dirs
    from shared_store import ProjectRuntime, StoreGate
    from storage_cleanup import migrate_database, cleanup_retired_sessions
    from workspace import Workspace

    # These worker-process values are used by managed path helpers and scripts.
    # The store and transport below receive their configuration explicitly.
    os.chdir(locations['project_dir'])
    os.environ["ALMOND_PROJECT_ROOT"] = locations["project_dir"]
    os.environ["ALMOND_MODEL_PATH"] = locations["model_path"]

    transport = BridgeTransport("127.0.0.1", args.port)
    runtime = ProjectRuntime(args, binding, locations)

    def bound_sender(payload_bytes, *positional, **keywords):
        return runtime.send(transport, payload_bytes, *positional, **keywords)

    # Serialize SQLite initialization, reindexing and closing checkpoints
    # against other workers sharing this project.
    with StoreGate(locations['storage']):
        migrate_database(locations, args.token)
        cleanup_retired_sessions(Path(locations['storage']), exclude_token=args.token)
        library_dirs = bound_library_dirs()
        application = create_server(
            state_db=db,
            library_dirs=library_dirs,
            send=bound_sender,
            execute_source=runtime.execute_rhinocode,
            exchange_reports=lambda: _exchange_reports(runtime),
        )
    worker_path = Path(locations['session_dir']) / 'worker.json'
    worker = read_json(worker_path)
    worker['library_dirs'] = library_dirs
    write_json(worker_path, worker)

    runtime.workspace = Workspace(locations, application.features.retrieval_store)
    mcp = application.mcp
    mcp.add_middleware(runtime)

    async def prepare():
        await register_tools(mcp, args, binding, locations, sender=bound_sender, runtime=runtime)
        if configure is not None:
            await configure(mcp, args, binding, locations, runtime)

    asyncio.run(prepare())
    from almond_mcp.modeling_guidance import startup_instructions

    mcp.instructions = startup_instructions()
    print("[AlmondParallel] Rhino target: {0}:{1}".format(
        transport.host, transport.port), file=sys.stderr)
    print("[AlmondParallel] Scene DB: {0}".format(db), file=sys.stderr)
    # Use the same MCP entry point as Almond's own cmd_serve.
    # stdout is reserved for the MCP protocol.
    print("[AlmondParallel] This is NOT a read-only service. Almond C# queries can create default layers.", file=sys.stderr)
    mcp.run()
    return 0
