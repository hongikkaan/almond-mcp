# User-made COS adapter

Follow `../../AGENTS.md` and `../mcp/runtime/AGENTS.md`.
Each client's lazy stdio adapter owns separate workers for its bound Rhinos. Engine handles
storage, native completion and helper compatibility. Do not duplicate these
policies in COS. Derive current schemas at client startup without importing the
DB-owning server; no manual catalog export is required. Preserve lockfile version,
session source fingerprint and worker schema checks. Register `../rhp/AlmondCOS/plugin-runtime/AlmondCOS.rhp`
with all dependencies beside it. Build/registration are not proof of live Rhino loading.

This module owns the external host, `rhp/` source, tests and `runtime-manifest.json`.
The RHP installation directory is retained for existing registrations only.
Maintain COS contracts in `SPEC.md`, without duplicating them in the root SPEC.
Use `build.ps1`, `run_tests.ps1`, and `configure.ps1` here. COS-only changes
must not require changes to MCP implementation or the Bridge manifest.
