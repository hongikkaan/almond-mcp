"""Disposable stdio worker exercising the real document-bound serve path.

No Rhino is launched and no native request is sent. All paths are supplied by
the test in an isolated temporary directory, including an empty .3dm placeholder.
"""
import argparse
import json
import ntpath
import os
from pathlib import Path

from project import STORAGE_PROTOCOL, connection_paths, process_start_ticks, write_json
from mcp_server import serve


def main():
    # Only this explicit fixture input supplies test documents. Production
    # startup still requires both final sources and has no fallback content.
    if os.environ.get("ALMOND_TEST_GUIDANCE_DIR"):
        from almond_mcp import modeling_guidance
        from almond_mcp.required_guidance import REQUIRED_DOCUMENTS
        folder = Path(os.environ["ALMOND_TEST_GUIDANCE_DIR"])
        modeling_guidance.REQUIRED_GUIDE_SOURCES = {name: folder / name for name in REQUIRED_DOCUMENTS}
    root = Path(os.environ["ALMOND_TEST_ROOT"])
    model = root / "disposable.3dm"
    reference_paths = json.loads(os.environ.get("ALMOND_TEST_REFERENCE_PATHS", json.dumps([str(root / "reference.3dm")])))
    model.write_bytes(b"")
    token = "a" * 32
    locations = connection_paths(model, "A", token, create=True)
    binding = {"schema": "almond-project", "token": token, "label": "A", "port": 5501,
               "storage_protocol": STORAGE_PROTOCOL, "valid": True, "pid": os.getpid(),
               "process_start_ticks": process_start_ticks(os.getpid()),
               **{key: locations[key] for key in ("model_path", "storage", "temp", "session_dir", "ready_path")}}
    write_json(locations["ready_path"], binding)
    write_json(Path(locations["session_dir"]) / "worker.json", {
        "token": token, "pid": os.getpid(), "process_start_ticks": process_start_ticks(os.getpid())})
    args = argparse.Namespace(port=5501, token=token, session=Path(locations["ready_path"]))
    async def configure(_mcp, _args, _binding, _locations, runtime):
        # Only the live observer is a test double; tool registration, workspace,
        # store, middleware and stdio transport use the real bound serve path.
        def observe(_sender, payload, *_positional, **_keywords):
            request = json.loads(payload)
            assert request["type"] == "get_rhino_context" and request["public_context"] is True
            catalogues = {"named_views": [{"name": "Arrival", "id": "fixture-view"}], "layouts": [],
                "worksession": {"attachments": [
                    {"filename": ntpath.basename(path), "path": path}
                    for path in reference_paths
                ]},
                "layers": [{"name": "Building", "id": "root", "parent_id": None},
                           {"name": "Wall", "id": "wall", "parent_id": "root"}]}
            values = {**catalogues, "document": {
                "name": model.name, "path": str(model), "runtime_serial_number": 1,
                "units": "Millimeters", "modified": False, "object_count": 0, "layer_count": 2}}
            assert set(request["sections"]) <= set(values)
            return json.dumps({"status": "success", "capabilities": {"context_sections": 4},
                               **{key: values[key] for key in request["sections"]}})
        runtime.send = observe
        runtime.workspace.store.create_phase(name="Fixture", file_name=model.name)

    return serve(args, binding, locations, Path(locations["state_db"]), configure=configure)


if __name__ == "__main__":
    raise SystemExit(main())
