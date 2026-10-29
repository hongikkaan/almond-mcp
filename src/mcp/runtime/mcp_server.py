"""External Almond MCP launcher for the editable checkout.

Example (Windows, outside Rhino):
  Normally started by the single top-level start button through codex.ps1.

The loopback endpoint is selected ONLY in this Python process's memory.
Models in one directory share DB. Connection metadata and scratch are separate.
The launcher uses internal module names, not an upstream-supported port option.
The existing sender wrapper adds connection/request identity in this process only.
"""
from __future__ import annotations
from almond_mcp.instruction_text import tool_instruction, read_instruction
from almond_mcp.modeling_guidance import project_instructions

import argparse
import asyncio
import json
import os
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path
from pydantic import StrictBool, StrictInt
from almond_mcp.managed_paths import relative_output, relative_path
from almond_mcp.query_output import project_query
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
        raise RuntimeError(read_instruction(__file__, 'response-90'))
    verify_process(binding)
    if binding['port'] != args.port:
        raise RuntimeError('Port and selected project disagree.')
    db = Path(locations['state_db'])
    if args.state_db is not None and args.state_db.resolve() != db:
        raise RuntimeError(read_instruction(__file__, 'response-92'))
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
                return serve(args, binding, locations, db, configure=configure)
            finally:
                worker["closed"] = True
                write_json(worker_path, worker)
    finally:
        from shared_store import StoreGate
        from storage_cleanup import cleanup_retired_sessions
        with StoreGate(locations["storage"]):
            cleanup_retired_sessions(Path(locations["storage"]))


async def configure_project_context(mcp, args, binding, locations, *, sender=None, runtime=None):
    """Register bound model and output path metadata for the current connection."""
    @mcp.tool()
    @tool_instruction(__file__, 'project_info')
    def project_info(sections: list[str] | None = None, include_ids: StrictBool = False) -> dict:
        sections = ["project", "document", "artifacts"] if sections is None else sections
        allowed = {"project", "document", "artifacts", "runtime", "instructions"}
        if not isinstance(sections, list) or any(section not in allowed for section in sections):
            raise ValueError("sections must contain project, document, artifacts, runtime or instructions.")
        current, _ = read_binding(args.session, args.token)
        if current != binding:
            raise RuntimeError(read_instruction(__file__, 'response-96'))
        verify_process(current)
        result = {"status": "success"}
        root = locations["project_dir"]
        if "project" in sections:
            result["project"] = {"project_root": root, "root_variable": "ALMOND_PROJECT_ROOT",
                "root_variable_set": os.environ.get("ALMOND_PROJECT_ROOT") == root,
                "file_name": Path(locations["model_path"]).name,
                "database": relative_path(locations["state_db"], root),
                "path_rule": "Managed tools apply ALMOND_PROJECT_ROOT automatically; pass relative paths."}
        if "document" in sections:
            if sender is None:
                raise RuntimeError("The live document observer is not connected.")
            live = json.loads(sender(b'{"type":"get_rhino_context","sections":["document"],"selection_limit":0}'))
            document = live.get("document")
            if live.get("status") != "success" or not isinstance(document, dict):
                result.update(status="error", live_document_checked=False,
                              message=live.get("message", "The live document observation is incomplete."))
                return result
            path = document.get("path")
            document["live_document_checked"] = True
            document["is_bound_document"] = bool(path and Path(path).resolve() == Path(locations["model_path"]).resolve())
            result["document"] = project_query(relative_output(document), include_ids=include_ids)
            if live.get("warnings"):
                result["warnings"] = live["warnings"]
        if "artifacts" in sections:
            result["artifacts"] = runtime.workspace.current() if runtime and runtime.workspace else {"artifact_dir": ""}
            result["artifacts"] = project_query(result["artifacts"], include_ids=include_ids)
            result["artifacts"]["path_rule"] = "Select a Plan with set_working_plan; managed outputs use its tmp/YYMMDD_name folder."
        if "runtime" in sections:
            result["runtime"] = relative_output({"slot": binding["label"], "port": binding["port"],
                "session_dir": locations["session_dir"], "scratch_root": str(Path(locations["temp"]) / "python"),
                "rhino_temp_at_attach": binding.get("rhino_temp"),
                "rhino_temp_note": "Rhino process TEMP at attach, not the artifact folder.",
                "python_executable": sys.executable, "attachment": binding.get("attachment", "external")})
            if runtime is not None:
                result["runtime"]["rhinocode"] = runtime.rhinocode_availability()
        if "instructions" in sections:
            result["instructions"] = project_instructions()
        return result

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    @tool_instruction(__file__, 'get_rhino_execution')
    def get_rhino_execution(request_id: str = "", include_result: StrictBool = True,
                            include_stdout: StrictBool = False, result_fields: list[str] | None = None,
                            offset: StrictInt = 0, limit: StrictInt = 100, include_ids: StrictBool = True,
                            include_diagnostics: StrictBool = False) -> dict:
        if runtime is None:
            raise RuntimeError("Managed RhinoCode execution is unavailable in this server.")
        if type(include_diagnostics) is not bool:
            raise ValueError("include_diagnostics must be a boolean.")
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("offset must be nonnegative and limit must be 1-1000 rows.")
        if result_fields is not None and (not isinstance(result_fields, list)
                or any(not isinstance(field, str) or not field for field in result_fields)):
            raise ValueError("result_fields must contain nonempty top-level result keys.")
        from rhinocode import execution_output
        result = runtime.get_rhino_execution(request_id, offset, limit, include_result, include_stdout, result_fields, include_ids)
        return execution_output(result, include_diagnostics=include_diagnostics)

    @mcp.tool()
    @tool_instruction(__file__, 'set_working_plan')
    def set_working_plan(plan_id: str, step_id: str = "", artifact_name: str = "") -> dict:
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        return {"status": "success", **runtime.workspace.select(plan_id, step_id, artifact_name)}

    @mcp.tool()
    @tool_instruction(__file__, 'rename_artifact_folder')
    def rename_artifact_folder(name: str, plan_id: str = "") -> dict:
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        return {"status": "success", **runtime.workspace.rename(name, plan_id)}

    @mcp.tool()
    @tool_instruction(__file__, 'execute_project_python')
    def execute_project_python(code: str, timeout_seconds: StrictInt = 60) -> dict:
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 600:
            raise ValueError("timeout_seconds must be 1-600.")
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        directory = runtime.workspace.artifact_path()
        directory.mkdir(parents=True, exist_ok=True)
        try:
            from python_runner import run_python
            result = run_python(code, directory, timeout_seconds)
            result["artifact_dir"] = relative_path(str(directory))
            if result["timed_out"]:
                result["message"] = "Python exceeded its time limit and was stopped. Existing artifacts were retained; do not automatically repeat writes."
            return result
        finally:
            try:
                directory.rmdir()
            except OSError:
                pass


def serve(args, binding, locations, db, *, configure=None):
    # No import-time SQLite access occurs before the project lease is acquired.
    os.chdir(locations['project_dir'])
    os.environ["ALMOND_PROJECT_ROOT"] = locations["project_dir"]
    os.environ["ALMOND_MODEL_PATH"] = locations["model_path"]

    # Must be set BEFORE server.py imports and creates its scene store.
    os.environ["RHINO_MCP_STATE_DB"] = str(db)

    from shared_store import ProjectRuntime, StoreGate
    # SQLite's initialization, reindex transactions and closing checkpoints must
    # not race a second worker. The original store and library resolver are used.
    with StoreGate(locations['storage']):
        from storage_cleanup import migrate_database, cleanup_retired_sessions
        migrate_database(locations, args.token)
        cleanup_retired_sessions(Path(locations['storage']), exclude_token=args.token)
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
    from workspace import Workspace
    runtime.workspace = Workspace(locations, server.retrieval_store)
    original_sender = server._send_and_receive

    def bound_sender(payload_bytes, *positional, **keywords):
        return runtime.send(original_sender, payload_bytes, *positional, **keywords)

    # Retain the existing process-local sender wrapper. The installed function's
    # socket/framing implementation is called unchanged with an owned envelope.
    server._send_and_receive = bound_sender
    server._execute_rhinocode = runtime.execute_rhinocode
    from compat_almond import install
    install(server, runtime)
    server.mcp.add_middleware(runtime)

    async def prepare():
        await configure_project_context(server.mcp, args, binding, locations, sender=server._send_and_receive, runtime=runtime)
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
