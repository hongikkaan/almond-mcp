"""External Almond MCP launcher for the editable checkout.

Example (Windows, outside Rhino):
  Normally started by the single top-level start button through codex.ps1.

The loopback endpoint is selected ONLY in this Python process's memory.
Models in one directory share DB. Connection metadata and scratch are separate.
The selected endpoint and managed sender are supplied when the server is built.
"""
from __future__ import annotations
from almond_mcp.tool_declarations import public_tool

import argparse
import sys
from importlib.metadata import version
from pathlib import Path
from pydantic import StrictBool, StrictInt
from almond_mcp.managed_paths import relative_path
from document_session import run_document_session
from project import read_binding, verify_process


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
    return run_document_session(
        args, register_tools=configure_project_context, validate_binding=validate_binding, configure=configure,
    )


async def configure_project_context(mcp, args, binding, locations, *, sender=None, runtime=None):
    """Register tools that use the current connection's workspace."""
    from almond_mcp.features.context.project_info import query_project_info
    from almond_mcp.tool_response import error_payload

    def verify_current_binding():
        current, _ = read_binding(args.session, args.token)
        if current != binding:
            raise RuntimeError('Connection changed. Exit Codex and reconnect with almond.')
        verify_process(current)

    @public_tool(mcp)
    def project_info(sections: list[str] | None = None, include_ids: StrictBool = False,
                     files_limit: StrictInt = 50, files_offset: StrictInt = 0) -> dict:
        return query_project_info(sections, include_ids, files_limit, files_offset,
                                  verify_binding=verify_current_binding, binding=binding,
                                  locations=locations, sender=sender, runtime=runtime)

    @public_tool(mcp, annotations={'readOnlyHint': False, 'destructiveHint': False})
    def upsert_project_file(file_name: str, description: str | None = None) -> dict:
        try:
            verify_current_binding()
            if runtime is None or runtime.workspace is None:
                raise RuntimeError("The project workspace is not connected.")
            record = runtime.workspace.store.upsert_project_file(file_name, description)
            return {"status": "success", **record}
        except (ValueError, RuntimeError) as exc:
            return error_payload(str(exc))

    @public_tool(mcp, annotations={'readOnlyHint': True, 'destructiveHint': False})
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

    @public_tool(mcp)
    def set_working_plan(plan_id: str, step_id: str = "", artifact_name: str = "", loop_no: StrictInt | None = None) -> dict:
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        return {"status": "success", **runtime.workspace.select(plan_id, step_id, artifact_name, loop_no)}

    @public_tool(mcp)
    def execute_looping(plan_id: str, resume: StrictBool = False, feedback: str = "", artifact_name: str = "") -> dict:
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        return {"status": "success", **runtime.workspace.execute_looping(plan_id, resume, feedback, artifact_name)}

    @public_tool(mcp)
    def rename_artifact_folder(name: str, plan_id: str = "") -> dict:
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        return {"status": "success", **runtime.workspace.rename(name, plan_id)}

    @public_tool(mcp)
    def execute_project_python(code: str, timeout_seconds: StrictInt = 60) -> dict:
        if not isinstance(code, str) or not code.strip():
            raise ValueError("code must be nonempty Python source.")
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 600:
            raise ValueError("timeout_seconds must be 1-600.")
        if runtime is None or runtime.workspace is None:
            raise RuntimeError("The project workspace is not connected.")
        directory = runtime.workspace.artifact_path(runtime.current_workspace())
        # Same process/document fence and late-result recovery as Rhino scripts.
        # Rhino runs asynchronously after CLI acknowledgement, so this tool must
        # never kill a Python child or remove its cwd when waiting expires.
        result = runtime.execute_rhinocode(code, "python", timeout_seconds,
                                          working_directory=str(directory))
        result["artifact_dir"] = relative_path(str(directory))
        return result


if __name__ == "__main__":
    try:
        from desktop_runtime import ensure_desktop_runtime
        ensure_desktop_runtime()
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print("[AlmondParallel] Startup/runtime error: {0}".format(exc), file=sys.stderr)
        raise SystemExit(1)
