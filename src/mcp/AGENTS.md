# MCP module

Follow `../../AGENTS.md`. Own the MCP API, modeling tools, execution runtime, CLI launchers, module tests and environment bootstrap. COS may consume the runtime's existing hooks; MCP must not import COS implementation or fixtures.
Keep MCP contracts in `SPEC.md`; update root documentation only for a real shared contract or dependency change.

Use `rebuild_environment.ps1 -Development` and `run_tests.ps1 -Development` for offline development without stopping everyday Rhino/MCP hosts. Keep live model/DB access out of default tests; use disposable fixtures. Shared schema/packaging/runtime integration checks belong to the root tests. Native modeling C# and the shared modeling_policy.json remain owned here and compiled by the Bridge; changing them requires a Bridge rebuild.
Run COS schema integration checks when changing a fingerprinted source. Fresh clients derive schemas automatically; restart the relevant client/session to load Python changes. Do not remove source/version checks to allow mixed workers.
Keep the stable interpreter location separate from source ownership.

The offline C# RhinoCode wrapper tests compile the actual template with Rhino API stubs using the .NET 8 SDK (`-DotNet` first, then checkout SDK and SDK-bearing PATH entries). They must not load Rhino or real documents; a missing SDK is an explicit prerequisite error, not a skip.

Keep BASIC-INSTRUCTIONS.md as the shared work guidance. get_modeling_guide() returns BASIC; tool selects an adjacent public-tool explanation. Keep the reader static and preserve source fingerprints; do not add topic routing or per-tool help switches.

## Runtime

All entry points use the same editable environment. Keep per-folder DB/tmp, per-token leases, A–J slots, process identity checks and native completion tracking. No session exclusively owns the shared DB. Do not remove locks to permit additional connections or retry uncertain native mutations.

Default library roots remain AppData; explicit overrides win. Call files belong under the bound `artifact_dir`. Preserve original helper wrappers and validation.
Do not modify upstream package files to bypass a user-made integration failure.

Context observations and block analysis belong to features/context; their native helpers compile into the Bridge. Component intersection helpers belong to features/components/native. Keep queries read-only, bounded and capability-gated. A public tool rename must update native dispatch, middleware and external schemas together.
