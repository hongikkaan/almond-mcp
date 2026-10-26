# tools.py explain

## list_library

<!-- instruction:list_library -->
Lists all available physics logic archetypes in the Grasshopper library.
Use this tool first to discover what logic IDs are available before
calling get_logic_by_id.

Returns:
    JSON list of logic IDs available (e.g., ["catenary", "bending", "01_simplebeam"]).
<!-- /instruction:list_library -->

## get_logic_by_id

<!-- instruction:get_logic_by_id -->
Retrieves parsed physics context for a specific Kangaroo2 or Karamba3D archetype.
Returns detected components, descriptions, and metadata extracted from the
Grasshopper binary file.

Args:
    logic_id: The filename (without extension) of the Grasshopper file.
              Use list_library() first to see available IDs.
              Examples: catenary, bending, 01_simplebeam
Returns:
    JSON string with detected physics components and context, or error.
<!-- /instruction:get_logic_by_id -->

## list_capsules

<!-- instruction:list_capsules -->
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
<!-- /instruction:list_capsules -->

## run_gh_definition

<!-- instruction:run_gh_definition -->
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
<!-- /instruction:run_gh_definition -->

## response-713

<!-- instruction:response-713 -->
Logic '{0}' not found. Use list_library() to see available IDs.
<!-- /instruction:response-713 -->

## response-714

<!-- instruction:response-714 -->
Unknown capsule_id: {0}. Use list_capsules() to discover capsules.
<!-- /instruction:response-714 -->

## response-727

<!-- instruction:response-727 -->
{0} declares unsupported type {1!r} in its manifest; fix the capsule sidecar before running it.
<!-- /instruction:response-727 -->
