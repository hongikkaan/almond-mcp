# MCP module

Follow `../../AGENTS.md`. Own the MCP API, modeling tools, execution runtime,
CLI launchers, module tests and environment bootstrap. COS may consume the
runtime's existing hooks; MCP must not import COS implementation or fixtures.
Keep MCP contracts in `SPEC.md`; update root documentation only for a real shared
contract or dependency change.

Use `rebuild_environment.ps1 -Development` and `run_tests.ps1 -Development`
for offline development without stopping everyday Rhino/MCP hosts. Keep live
model/DB access out of default tests; use disposable fixtures. Shared schema/packaging/runtime integration
checks belong to the root tests. Native modeling C# and modeling policy remain
owned here and compiled by the Bridge; changing them requires a Bridge rebuild.
Run COS schema integration checks when changing a fingerprinted source. Fresh
clients derive schemas automatically; restart the relevant client/session to
load Python changes. Do not remove source/version checks to allow mixed workers.
Keep the stable interpreter location separate from source ownership.
