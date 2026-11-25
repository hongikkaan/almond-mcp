"""Disposable stdio worker exercising the RhinoTerminal document-bound entry.

No Rhino is launched and no native request is sent. All paths are supplied by
the test in an isolated temporary directory, including an empty .3dm placeholder.
"""
import base64
import io
import json
import os
from pathlib import Path

from project import STORAGE_PROTOCOL, connection_paths, process_start_ticks, read_json, write_json
from mcp_server import main as run_document_server


def main():
    root = Path(os.environ["ALMOND_TEST_ROOT"])
    model = root / os.environ.get("ALMOND_TEST_MODEL", "disposable.3dm")
    model.write_bytes(b"")
    token = os.environ.get("ALMOND_TEST_TOKEN", "a" * 32)
    slot = os.environ.get("ALMOND_TEST_SLOT", "A")
    port = 5501 + ord(slot) - ord("A")
    locations = connection_paths(model, slot, token, create=True)
    binding = {"schema": "almond-project", "token": token, "label": slot, "port": port,
               "document_serial": 1,
               "storage_protocol": STORAGE_PROTOCOL, "valid": True, "pid": os.getpid(),
               "process_start_ticks": process_start_ticks(os.getpid()),
               **{key: locations[key] for key in ("model_path", "storage", "temp", "session_dir", "ready_path")}}
    write_json(locations["ready_path"], binding)

    async def configure(_mcp, _args, _binding, _locations, runtime):
        # Only the live observer is a test double; tool registration, workspace,
        # store, middleware and stdio transport use the real bound serve path.
        def observe(_sender, payload, *_positional, **_keywords):
            request = json.loads(payload)
            if request == {"type": "get_rhino_context", "sections": [], "selection_limit": 0}:
                return json.dumps({"status": "success", "capabilities": {"view_capture": 1, "display_mode_menu": 1}})
            if request["type"] == "get_defined_viewcapture":
                from PIL import Image
                assert Path(request["expected_model_path"]) == model
                work = runtime.current_workspace()
                selected = read_json(runtime.workspace.state_path)
                assert {key: work[key] for key in selected} == selected
                assert work["step_id"] and work["artifact_dir"] == os.environ["ALMOND_ARTIFACT_DIR"]
                output = io.BytesIO()
                Image.new("RGB", (30, 30), "#" + token[0] * 3).save(output, format="PNG")
                return json.dumps({"status": "success", "image": {
                    "mime_type": "image/png", "data": base64.b64encode(output.getvalue()).decode("ascii"),
                    "width": 30, "height": 30, "source_width": 40, "source_height": 40}})
            assert request == {"type": "get_rhino_context",
                               "sections": ["document", "named_views", "layouts", "layer_tree", "worksession_files"],
                               "public_context": True, "selection_limit": 0}
            return json.dumps({"status": "success", "worksession_files": [],
                               "named_views": [], "layouts": [], "layer_tree": [], "document": {
                "name": model.name, "path": str(model), "runtime_serial_number": 1,
                "units": "Millimeters", "modified": False, "object_count": 0, "layer_count": 1}})
        runtime.send = observe
        runtime.workspace.store.upsert_project_file(model.name)
        runtime.workspace.store.create_phase(name="Fixture", file_name=model.name)

    return run_document_server(["--port", str(port), "--token", token, "--session", locations["ready_path"]],
                               configure=configure)


if __name__ == "__main__":
    raise SystemExit(main())
