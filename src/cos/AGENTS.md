# External MCP connectors and AlmondRhino

Follow `../../AGENTS.md` and `../mcp/AGENTS.md`.
Each client's lazy stdio adapter owns separate workers for its bound Rhinos. Engine handles storage, native completion and helper compatibility. Do not duplicate these policies in the external connectors. Derive current schemas at client startup without importing the DB-owning server; no manual catalog export is required. Preserve lockfile version, session source fingerprint and worker schema checks. Register `../rhp/AlmondRhino/plugin-runtime/AlmondRhino.rhp` with all dependencies beside it. Build/registration are not proof of live Rhino loading.

This module owns the external host, `rhp/` source, tests and `runtime-manifest.json`.
The RHP is AlmondRhino; the CoS app and beyond share it. Follow the root glossary for product and route names.
Maintain external connector and AlmondRhino contracts in `SPEC.md`, without duplicating them in the root SPEC.
Use `run_tests.ps1 -Development` with the MCP development environment for
offline fixtures while everyday hosts stay running. `build.ps1` and `configure.ps1`
are deployment steps, not prerequisites for a running Rhino/MCP server during tests. Module-only changes
must not require changes to MCP implementation or the Bridge manifest.
