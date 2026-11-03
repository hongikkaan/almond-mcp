# tools.py explain

## list_library

<!-- instruction:list_library -->
List the local Grasshopper logic names available for retrieval.

When to use: Discover an archetype name when get_logic_by_id's logic_id is not already known.
Before calling: No inputs or live Rhino connection are needed; optional field_groups selects extra output.
Inputs from earlier results: None required. Pass an exact logic_names entry to get_logic_by_id.logic_id; include_ids=true additionally retains logic_ids.
Interpretation: total_entries is the index count, and logic_names contains filename stems, not solved physics results. field_groups=["paths"] adds library_dir.
Limits: Presence in this index does not establish execution readiness or an audited capsule contract; use capsule discovery for that distinction. This call only reads the existing index.

Returns:
    JSON list of logic IDs available (e.g., ["catenary", "bending", "01_simplebeam"]).
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds ports, definition, source, paths, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:list_library -->

## get_logic_by_id

<!-- instruction:get_logic_by_id -->
Retrieve parsed Grasshopper component context or JSON-sidecar metadata for a local logic name without executing it.

When to use: Inspect a Kangaroo2/Karamba3D archetype or an attached capsule contract before reuse.
Before calling: Supply a known filename stem as logic_id; list_library can discover unknown names but is not required for a known one.
Inputs from earlier results: Use list_library.logic_names, or list_capsules.definition_file's stem obtained with field_groups=["definition"]. When present, metadata.capsule.inputs supplies exact names/types/units/required flags for run_gh_definition.inputs; metadata.capsule.outputs supplies output semantics. Request include_ids=true to retain nested capsule_id.
Interpretation: Parsed components, all_descriptions and metadata remain in the default payload; field_groups=["source"] exposes a sidecar source and ["paths"] exposes available path fields. The reader prefers GHX over GH, or returns metadata alone for JSON-only entries.
Limits: Components are detected by binary-string scanning, not graph evaluation or a verified dependency graph. Missing/invalid capsule metadata does not establish an executable contract; no solve, baking or model change occurs.

Args:
    logic_id: The filename (without extension) of the Grasshopper file.
              Use list_library() first to see available IDs.
              Examples: catenary, bending, 01_simplebeam
Returns:
    JSON string with detected physics components and context, or error.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds ports, definition, source, paths, audit, or all; the requested manifest/parsed logic/script remains in the default payload.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_logic_by_id -->

## list_capsules

<!-- instruction:list_capsules -->
List compact Grasshopper capsule cards and distinguish audited executable definitions from retrieval-only context.

When to use: Choose a capsule by capability or find its declared input/output port names.
Before calling: Optionally filter capability and audited_only; no live solve is performed.
Inputs from earlier results: None required. Request include_ids=true to obtain capsules[].capsule_id for run_gh_definition.capsule_id, and field_groups=["ports","definition"] for inputs/outputs names and definition_file. Use that filename's stem with get_logic_by_id to inspect metadata.capsule's typed contract when available.
Interpretation: audited=true is the runner's eligibility gate, not an engineering confidence rating. The ports group contains names only, not their types, units, defaults or semantics.
Limits: audited=false capsules cannot run. At most 50 cards are returned; total and next_offset can indicate more matches, but this tool exposes no offset input. Default summary omits both capsule IDs and port lists; discovery alone does not verify outputs or plugin availability.

Args:
    capability: Optional filter: "analyze", "generate", "form_find", or "aggregate".
    audited_only: When true, list only capsules that run_gh_definition will accept.
Returns:
    JSON with total and a list of compact capsule cards.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds ports, definition, source, paths, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:list_capsules -->

## run_gh_definition

<!-- instruction:run_gh_definition -->
Execute an audited Grasshopper capsule through the live Rhino bridge and return its declared outputs.

When to use: Run a known typed capsule for analysis, generation, form-finding or aggregation.
Before calling: Confirm audited=true, the required contract ports and their units; ensure referenced geometry already exists in the connected document. Known contracts can be reused without mandatory discovery calls.
Inputs from earlier results: Use list_capsules.capsules[].capsule_id with include_ids=true. Its ports group gives names only; get_logic_by_id.metadata.capsule, when present, supplies types/units/required flags. Map exact ALMOND_IN_* names to {"guids":["<object-guid>"]} for geometry, raw JSON scalars for number/integer/string/bool, or flat primitive arrays for their list types. Use confirmed existing object handles, not library/scene IDs.
Interpretation: Read outputs by ALMOND_OUT_* name using manifest semantics and units. analysis_method/confidence reflect the manifest declaration (api/high, template/medium, rule_based/low), not independent certification; report them with warnings. Rule-based/low is an estimate, not FEA. baked_guids identifies geometry the definition baked into the document.
Limits: Unknown ports, missing required values and unsupported types are rejected before sending. No client-side unit conversion occurs; omitted optional ports use definition defaults. Execution can change the document. timeout_s is a solver budget of >0 to 600 seconds, not proof of rollback or non-execution after a timeout.

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
