"""Scope the inspected asset helpers' reports to the current engine operation."""
from __future__ import annotations

from functools import wraps
import json
from pathlib import Path
from types import FunctionType, SimpleNamespace
from uuid import uuid4


REPORTS = {
    "almond_matgroups.txt": 'Path.Combine(Path.GetTempPath(), "almond_matgroups.txt")',
    "almond_imported.txt": 'Path.Combine(Path.GetTempPath(), "almond_imported.txt")',
    "almond_import_report.json": 'System.IO.Path.Combine(System.IO.Path.GetTempPath(), "almond_import_report.json")',
}


def call_scoped(original, server, folder: Path, allowed: set[str], args, kwargs):
    folder.mkdir(parents=True, exist_ok=False)
    sent: set[str] = set()

    def scoped_sender(payload, *positional, **keywords):
        request = json.loads(payload)
        if request == {"type": "get_rhino_context", "selection_limit": 0}:
            return server._send_and_receive(payload, *positional, **keywords)
        if request.get("type") != "execute" or not isinstance(request.get("script"), str):
            raise RuntimeError("Unsupported Almond asset helper payload.")
        script = request["script"]
        matches = [name for name in allowed if REPORTS[name] in script]
        if len(matches) != 1 or script.count(REPORTS[matches[0]]) != 1 or matches[0] in sent:
            raise RuntimeError("Almond asset helper report contract changed.")
        name = matches[0]
        literal = '@"' + str(folder / name).replace('"', '""') + '"'
        request["script"] = script.replace(REPORTS[name], literal, 1)
        sent.add(name)
        # Keep the current operation's binding checks and native completion tracking.
        return server._send_and_receive(json.dumps(request).encode("utf-8"), *positional, **keywords)

    feature_context = getattr(server, "_feature_context", None)
    if feature_context is not None:
        with feature_context.override(
            tempfile=SimpleNamespace(gettempdir=lambda: str(folder)),
            _send_and_receive=scoped_sender,
        ):
            return original(*args, **kwargs)

    # Keep the existing adapter for callers supplying module-level helpers.
    namespace = dict(original.__globals__)
    namespace.update(tempfile=SimpleNamespace(gettempdir=lambda: str(folder)),
                     _send_and_receive=scoped_sender)
    scoped = FunctionType(original.__code__, namespace, original.__name__,
                          original.__defaults__, original.__closure__)
    scoped.__kwdefaults__ = original.__kwdefaults__
    return scoped(*args, **kwargs)


def install(server, runtime) -> None:
    base = Path(runtime.locations["call_root"])
    material = server._material_groups
    receive = server._receive_contract

    def new_folder():
        batch = runtime.scope.get()
        if batch is None or batch.sealed:
            raise RuntimeError("No active operation for Almond asset helper reports.")
        return base / batch.operation_id / "helpers" / uuid4().hex

    @wraps(material)
    def material_groups(*args, **kwargs):
        folder = new_folder()
        result = call_scoped(material, server, folder, {"almond_matgroups.txt"}, args, kwargs)
        if not (folder / "almond_matgroups.txt").is_file():
            raise RuntimeError("Rhino material report was not received; export metadata is unverified.")
        return result

    @wraps(receive)
    def receive_contract(*args, **kwargs):
        folder = new_folder()
        result = call_scoped(receive, server, folder,
                             {"almond_imported.txt", "almond_import_report.json"}, args, kwargs)
        if result.get("status") == "success":
            try:
                report = json.loads((folder / "almond_import_report.json").read_text(encoding="utf-8"))
                if not isinstance(report, dict) or not {"stamped", "deduped", "width", "depth", "height"} <= report.keys():
                    raise ValueError("Incomplete import report")
            except (OSError, ValueError):
                return {
                    "status": "error",
                    "message": "Geometry was imported, but its report is unverified. Inspect the existing objects before any retry.",
                    "imported_guids": result.get("imported_guids", []),
                    "report_path": str(folder / "almond_import_report.json"),
                }
        return result

    server._material_groups = material_groups
    server._receive_contract = receive_contract
