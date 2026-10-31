"""Disposable stdio worker exercising the real document-bound serve path.

No Rhino is launched and no native request is sent. All paths are supplied by
the test in an isolated temporary directory, including an empty .3dm placeholder.
"""
import argparse
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
    return serve(args, binding, locations, Path(locations["state_db"]))


if __name__ == "__main__":
    raise SystemExit(main())
