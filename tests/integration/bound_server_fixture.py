"""Disposable stdio worker exercising the real document-bound serve path.

No Rhino is launched and no native request is sent. All paths are supplied by
the test in an isolated temporary directory, including an empty .3dm placeholder.
"""
import argparse
import json
import os
from pathlib import Path

from project import STORAGE_PROTOCOL, connection_paths, process_start_ticks, write_json
from mcp_server import serve


def main():
    root = Path(os.environ["ALMOND_TEST_ROOT"])
    model = root / "disposable.3dm"
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
            assert json.loads(payload) == {"type": "get_rhino_context", "sections": ["document"], "selection_limit": 0}
            return json.dumps({"status": "success", "document": {
                "name": model.name, "path": str(model), "runtime_serial_number": 1,
                "units": "Millimeters", "modified": False, "object_count": 0, "layer_count": 1}})
        runtime.send = observe
        runtime.workspace.store.create_phase(name="Fixture", file_name=model.name)

    return serve(args, binding, locations, Path(locations["state_db"]), configure=configure)


if __name__ == "__main__":
    raise SystemExit(main())
