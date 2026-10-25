"""Register Grasshopper tools against the owning server's current services."""
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
            f"{name} declares unsupported type {port_type!r} in its manifest; "
            "fix the capsule sidecar before running it."
        )
    return None


def register(mcp, context):
    """Register the existing Grasshopper MCP surface without import-time effects."""

    @mcp.tool()
    def list_library() -> str:
        """
        Lists all available physics logic archetypes in the Grasshopper library.
        Use this tool first to discover what logic IDs are available before
        calling get_logic_by_id.

        Returns:
            JSON list of logic IDs available (e.g., ["catenary", "bending", "01_simplebeam"]).
        """
        return json.dumps({
            "library_dir": context.LIBRARY_DIR,
            "total_entries": len(context.indexer.index),
            "logic_ids": context.indexer.list_ids(),
        })


    @mcp.tool()
    def get_logic_by_id(logic_id: str) -> str:
        """
        Retrieves parsed physics context for a specific Kangaroo2 or Karamba3D archetype.
        Returns detected components, descriptions, and metadata extracted from the
        Grasshopper binary file.

        Args:
            logic_id: The filename (without extension) of the Grasshopper file.
                      Use list_library() first to see available IDs.
                      Examples: catenary, bending, 01_simplebeam
        Returns:
            JSON string with detected physics components and context, or error.
        """
        query_id = logic_id.lower()
        file_map = context.indexer.index.get(query_id)

        if not file_map:
            return json.dumps({"error": f"Logic '{logic_id}' not found. Use list_library() to see available IDs."})

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
    def list_capsules(capability: str = "", audited_only: bool = False) -> str:
        """
        Lists Grasshopper capsules: GH definitions with a typed, audited input/output
        contract that can be executed via run_gh_definition.

        Call this FIRST to discover what capsules exist before calling run_gh_definition.
        Each entry is a compact card with capsule_id, capability, structure_type,
        audited flag, and the reserved ALMOND_IN_* / ALMOND_OUT_* port names. Only
        capsules with audited=true can actually run; audited=false capsules are
        retrieval context only (read them via get_logic_by_id instead).

        Args:
            capability: Optional filter: "analyze", "generate", "form_find", or "aggregate".
            audited_only: When true, list only capsules that run_gh_definition will accept.
        Returns:
            JSON with total and a list of compact capsule cards.
        """
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
    def run_gh_definition(
        capsule_id: str,
        inputs: dict,
        seed: int | None = None,
        timeout_s: float = 60.0,
    ) -> str:
        """
        Runs an audited Grasshopper capsule (GH definition + typed contract) through
        the Rhino bridge and returns its declared outputs.

        Workflow: call list_capsules() first to pick a capsule_id and see its input/
        output port names. Create any geometry with execute_rhino_script, then pass
        the returned GUIDs here. Inputs are validated client-side against the capsule
        manifest before anything is sent to Rhino, so errors from this tool name the
        exact port at fault.

        Input value forms (keyed by the exact ALMOND_IN_* port name):
          - Geometry ports (point/curve/mesh/brep and their [] list forms):
            {"guids": ["<rhino-object-guid>", ...]} referencing objects already in
            the Rhino document.
          - number / integer / string / bool ports: the raw JSON value.
          - number[] / integer[] / string[] ports: a flat JSON list.
        Units are declared per port in the manifest — supply values in those units;
        nothing is guessed or auto-converted client-side. Optional inputs may be
        omitted; the capsule's declared defaults then apply inside the definition.

        Only audited capsules run. audited=false means the GHX has no verified
        ALMOND_IN_*/ALMOND_OUT_* harness params yet; this tool refuses it
        (see asset/capsules/AUTHORING.md for how to harness one).

        The response's "outputs" object is keyed by ALMOND_OUT_* names; interpret
        each value using the manifest's semantics field (e.g. max_nodal_displacement,
        per_element_utilization) and declared units. The response also carries
        analysis_method (api|template|rule_based), confidence (high|medium|low),
        warnings, and baked_guids — report method and confidence honestly;
        rule_based/low means an estimate, not FEA.

        Args:
            capsule_id: Stable capsule identifier from list_capsules (e.g. "karamba_beam_v1").
            inputs: Object mapping ALMOND_IN_* port names to values (forms above).
            seed: Optional integer seed for stochastic definitions; omit for deterministic ones.
            timeout_s: Solver budget in seconds (default 60, max 600).
        Returns:
            JSON with status, capsule_id, outputs, baked_guids, analysis_method,
            confidence, warnings, and error — or a validation error naming the
            offending input and the valid port names.
        """
        manifest = context.retrieval_store.get_capsule(capsule_id)
        if not manifest:
            listing = context.retrieval_store.search_capsules(limit=50)
            return json.dumps({
                "status": "error",
                "message": f"Unknown capsule_id: {capsule_id}. Use list_capsules() to discover capsules.",
                "available_capsules": [
                    capsule["capsule_id"] for capsule in listing["capsules"]
                ],
            })

        if not manifest.get("audited"):
            return json.dumps({
                "status": "error",
                "message": (
                    f"Capsule '{capsule_id}' is not audited: its definition has no verified "
                    "ALMOND_IN_*/ALMOND_OUT_* harness params, so run_gh_definition refuses to "
                    "execute it. It remains available as retrieval context (get_logic_by_id). "
                    "See asset/capsules/AUTHORING.md for how to harness and audit the definition."
                ),
            })

        if not isinstance(inputs, dict):
            return json.dumps({
                "status": "error",
                "message": "inputs must be an object keyed by ALMOND_IN_* port names.",
            })

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
            return json.dumps({
                "status": "error",
                "message": "timeout_s must be a number between 0 (exclusive) and 600 seconds.",
            })

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
            return json.dumps({
                "status": "error",
                "message": f"Capsule '{capsule_id}' timed out (>{timeout_s}s solver budget).",
            })
        except ConnectionRefusedError:
            return json.dumps({
                "status": "error",
                "message": "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?",
            })
        except Exception as e:
            return json.dumps({"status": "error", "message": f"Bridge error: {e}"})

    return {
        "list_library": list_library,
        "get_logic_by_id": get_logic_by_id,
        "list_capsules": list_capsules,
        "run_gh_definition": run_gh_definition,
        "_capsule_input_error": _capsule_input_error,
    }
