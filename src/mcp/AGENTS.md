# MCP module

Follow `../../AGENTS.md`. Own the MCP API, modeling tools, execution runtime,
CLI launchers, module tests and environment bootstrap. COS may consume the
runtime's existing hooks; MCP must not import COS implementation or fixtures.
Keep MCP contracts in `SPEC.md`; update root documentation only for a real shared
contract or dependency change.

Run `run_tests.ps1` for this module. Shared schema/packaging/runtime integration
checks belong to the root tests. Native modeling C# and modeling policy remain
owned here and compiled by the Bridge; changing them requires a Bridge rebuild.
Rebuild a COS catalog when changing a source covered by its fingerprint.
Keep the stable interpreter location separate from source ownership.
