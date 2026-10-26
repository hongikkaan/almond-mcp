"""Register Grasshopper tools against the owning server's current services."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output
from almond_mcp.instruction_text import tool_instruction, read_instruction
from pydantic import StrictBool
import json
import os
import socket

from almond_mcp.features.grasshopper.ghx_parser import GHParser


_CAPSULE_GEOMETRY_TYPES = {
    "point", "point[]",
    "curve", "curve[]",
    "mesh", "mesh[]",
    "brep", "brep[]",
}


def _capsule_input_error(port: dict, value) -> str | None:
    """Validate one capsule input value against its manifest port declaration.

    Returns a human-readable error string, or None when the value satisfies the
    contract. Geometry ports must arrive as {"guids": [...]} references to
    objects already in the Rhino document; primitive ports must match their
    declared JSON type exactly.
    """
    name = port.get("name", "?")
    port_type = str(port.get("type", ""))
    units = port.get("units", "")
    units_note = f" (units: {units})" if units else ""

    def _is_number(item) -> bool:
        return (
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and abs(item) != float("inf")
            and item == item
        )

    if port_type in _CAPSULE_GEOMETRY_TYPES:
        if (
            not isinstance(value, dict)
            or set(value.keys()) != {"guids"}
            or not isinstance(value.get("guids"), list)
            or not value["guids"]
            or not all(isinstance(guid, str) and guid.strip() for guid in value["guids"])
        ):
            return (
                f'{name} ({port_type}) must be a GUID reference of the exact form '
                '{"guids": ["<rhino-object-guid>", ...]} with at least one GUID string, '
                "referencing objects already in the Rhino document."
            )
        return None

    if port_type == "number":
        if not _is_number(value):
            return f"{name} must be a finite number{units_note}."
    elif port_type == "integer":
        if not (isinstance(value, int) and not isinstance(value, bool)):
            return f"{name} must be an integer{units_note}."
    elif port_type == "bool":
        if not isinstance(value, bool):
            return f"{name} must be a boolean."
    elif port_type == "string":
        if not isinstance(value, str):
            return f"{name} must be a string."
    elif port_type == "number[]":
        if not (isinstance(value, list) and all(_is_number(item) for item in value)):
            return f"{name} must be a flat list of finite numbers{units_note}."
    elif port_type == "integer[]":
        if not (
            isinstance(value, list)
            and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
        ):
            return f"{name} must be a flat list of integers{units_note}."
    elif port_type == "string[]":
        if not (isinstance(value, list) and all(isinstance(item, str) for item in value)):
            return f"{name} must be a flat list of strings."
    else:
        return (
            read_instruction(__file__, 'response-727').format(name, port_type)
        )
    return None


def register(mcp, context):
    """Register the existing Grasshopper MCP surface without import-time effects."""

    @mcp.tool()
    @tool_instruction(__file__, 'list_library')
    @query_output
    def list_library(include_ids: StrictBool = False) -> str:
        return json.dumps({
            "library_dir": context.LIBRARY_DIR,
            "total_entries": len(context.indexer.index),
            "logic_ids": context.indexer.list_ids(),
        })


    @mcp.tool()
    @tool_instruction(__file__, 'get_logic_by_id')
    @query_output
    def get_logic_by_id(logic_id: str, include_ids: StrictBool = False) -> str:
        query_id = logic_id.lower()
        file_map = context.indexer.index.get(query_id)

        if not file_map:
            return json.dumps({"error": read_instruction(__file__, 'response-713').format(logic_id)})

        # Prioritize GHX > GH > JSON-only
        target_file = file_map.get('ghx') or file_map.get('gh')
        target_json = file_map.get('json')

        # If only a JSON sidecar exists, return it directly
        if target_json and not target_file:
            try:
                with open(target_json, 'r') as f:
                    data = json.load(f)
                return json.dumps({"logic_id": logic_id, "source": target_json, "metadata": data})
            except Exception as e:
                return json.dumps({"error": f"Failed to read JSON sidecar: {e}"})

        # Parse via the binary string extractor
        try:
            parser = GHParser(target_file)
            physics_context = parser.parse()
            return physics_context.model_dump_json()
        except Exception as e:
            return json.dumps({"error": f"Failed to parse '{target_file}': {str(e)}"})


    @mcp.tool()
    @tool_instruction(__file__, 'list_capsules')
    @query_output
    def list_capsules(capability: str = "", audited_only: bool = False, include_ids: StrictBool = False) -> str:
        page = context.retrieval_store.search_capsules(
            capability=capability,
            audited_only=audited_only,
            limit=50,
        )
        return json.dumps({
            "capsule_library_dir": context.CAPSULE_LIBRARY_DIR,
            **page,
        })


    @mcp.tool()
    @tool_instruction(__file__, 'run_gh_definition')
    def run_gh_definition(
        capsule_id: str,
        inputs: dict,
        seed: int | None = None,
        timeout_s: float = 60.0,
    ) -> str:
        manifest = context.retrieval_store.get_capsule(capsule_id)
        if not manifest:
            listing = context.retrieval_store.search_capsules(limit=50)
            return json.dumps({
                "status": "error",
                "message": read_instruction(__file__, 'response-714').format(capsule_id),
                "available_capsules": [
                    capsule["capsule_id"] for capsule in listing["capsules"]
                ],
            })

        if not manifest.get("audited"):
            return json.dumps(error_payload(f"Capsule '{capsule_id}' is not audited: its definition has no verified "
                    "ALMOND_IN_*/ALMOND_OUT_* harness params, so run_gh_definition refuses to "
                    "execute it. It remains available as retrieval context (get_logic_by_id). "
                    "See asset/capsules/AUTHORING.md for how to harness and audit the definition."))

        if not isinstance(inputs, dict):
            return json.dumps(error_payload("inputs must be an object keyed by ALMOND_IN_* port names."))

        ports = {
            port["name"]: port
            for port in manifest.get("inputs", [])
            if isinstance(port, dict) and isinstance(port.get("name"), str)
        }
        valid_names = sorted(ports)

        unknown = sorted(set(inputs) - set(ports))
        if unknown:
            return json.dumps({
                "status": "error",
                "message": f"Unknown input name(s) for '{capsule_id}': {', '.join(unknown)}.",
                "valid_inputs": valid_names,
            })

        missing = sorted(
            name for name, port in ports.items()
            if port.get("required", True) and name not in inputs
        )
        if missing:
            return json.dumps({
                "status": "error",
                "message": f"Missing required input(s) for '{capsule_id}': {', '.join(missing)}.",
                "valid_inputs": valid_names,
            })

        problems = []
        for name in sorted(inputs):
            problem = _capsule_input_error(ports[name], inputs[name])
            if problem:
                problems.append(problem)
        if problems:
            return json.dumps({
                "status": "error",
                "message": "Input validation failed: " + " ".join(problems),
                "valid_inputs": valid_names,
            })

        if not (isinstance(timeout_s, (int, float)) and not isinstance(timeout_s, bool)
                and timeout_s == timeout_s and 0 < timeout_s <= 600):
            return json.dumps(error_payload("timeout_s must be a number between 0 (exclusive) and 600 seconds."))

        manifest_path = manifest.get("_manifest_path") or os.path.join(
            context.CAPSULE_LIBRARY_DIR, f"{capsule_id}.capsule.json"
        )

        payload = json.dumps({
            "type": "run_definition",
            "capsule_id": capsule_id,
            "manifest_path": manifest_path,
            "inputs": inputs,
            "seed": seed,
            "timeout_s": timeout_s,
        }).encode("utf-8")

        try:
            # Socket budget exceeds the solver budget so the bridge can report its
            # own timeout as structured JSON instead of a dead connection.
            return context._send_and_receive(payload, timeout=float(timeout_s) + 15.0)
        except socket.timeout:
            return json.dumps(error_payload(f"Capsule '{capsule_id}' timed out (>{timeout_s}s solver budget)."))
        except ConnectionRefusedError:
            return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"))
        except Exception as e:
            return json.dumps(error_payload(f"Bridge error: {e}"))

    return {
        "list_library": list_library,
        "get_logic_by_id": get_logic_by_id,
        "list_capsules": list_capsules,
        "run_gh_definition": run_gh_definition,
        "_capsule_input_error": _capsule_input_error,
    }
