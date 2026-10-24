# User-made COS adapter

Follow `../../AGENTS.md` and `../mcp/runtime/AGENTS.md`.
One stdio host owns separate workers for each bound Rhino. Engine handles
storage, native completion and helper compatibility. Do not duplicate these
policies in COS. Preserve source/schema checks; regenerate the catalog without
importing the DB-owning server. Register `../rhp/AlmondCOS/plugin-runtime/AlmondCOS.rhp`
with all dependencies beside it. Build/registration are not proof of live Rhino loading.

This module owns the external host, `rhp/` source, tests and `runtime-manifest.json`.
The RHP installation directory is retained for existing registrations only.
Maintain COS contracts in `SPEC.md`, without duplicating them in the root SPEC.
Use `build.ps1`, `run_tests.ps1`, and `configure.ps1` here. COS-only changes
must not require changes to MCP implementation or the Bridge manifest.
