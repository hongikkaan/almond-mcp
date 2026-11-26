"""Open a disposable bound worker with a simulated native transport."""
import base64
import io
import json
import os
from pathlib import Path
import sys

from PIL import Image

from almond_mcp.bridge_transport import BridgeTransport
from mcp_server import main as run_worker
from project import STORAGE_PROTOCOL, connection_paths, process_start_ticks, write_json


def native_transport(model, token, session):
    sequence = 0

    def respond(_transport, payload, **_options):
        nonlocal sequence
        request = json.loads(payload)
        operation = json.loads(request["payload"])
        match operation["type"]:
            case "get_rhino_context":
                value = {"status": "success", "capabilities": {"view_capture": 1, "display_mode_menu": 1}}
            case "get_defined_viewcapture" if Path(operation["expected_model_path"]) == model:
                output = io.BytesIO()
                Image.new("RGB", (128, 128), "#" + token[0] * 3).save(output, format="PNG")
                value = {"status": "success", "image": {
                    "mime_type": "image/png", "data": base64.b64encode(output.getvalue()).decode("ascii"),
                    "width": 128, "height": 128, "source_width": 128, "source_height": 128,
                }}
            case _:
                raise ValueError(f"Fixture cannot serve {operation['type']} for {model.name}")

        # The bound worker requires a receipt for the exact completed frame.
        sequence += 1
        identity = {key: request[key] for key in ("token", "operation_id", "request_id", "storage_protocol")}
        write_json(session / "native.json", {**identity, "schema": "almond-native", "pending": 0,
                   "sequence": sequence, "completion_status": "completed"})
        return json.dumps({**identity, "schema": "almond-native-response", "native_sequence": sequence,
                           "completion_status": "completed", "payload": json.dumps(value)})

    return respond


def main(model_name):
    root = Path(os.environ["ALMOND_TEST_ROOT"]).resolve(strict=True)
    model = (root / model_name).resolve(strict=True)
    if model.parent != root or not model.is_file():
        raise ValueError("Use a model fixture inside the scratch directory")
    token = os.environ.get("ALMOND_TEST_TOKEN", "a" * 32)
    slot = os.environ.get("ALMOND_TEST_SLOT", "A")
    port = 5501 + ord(slot) - ord("A")
    locations = connection_paths(model, slot, token, create=True)
    binding = {"schema": "almond-project", "token": token, "label": slot, "port": port,
               "document_serial": 1, "storage_protocol": STORAGE_PROTOCOL, "valid": True,
               "pid": os.getpid(), "process_start_ticks": process_start_ticks(os.getpid()),
               **{key: locations[key] for key in ("model_path", "storage", "temp", "session_dir", "ready_path")}}
    write_json(locations["ready_path"], binding)
    BridgeTransport.__call__ = native_transport(model, token, Path(locations["session_dir"]))
    return run_worker(["--port", str(port), "--token", token, "--session", locations["ready_path"]])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
