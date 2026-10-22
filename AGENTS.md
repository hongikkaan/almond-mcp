# Personal Almond fork

## Layout and ownership

Read `SPEC.md` for the structure and `LOCAL_SETUP.md` for execution/build paths.
This checkout is the `mcp/almond-mcp` submodule of the local Rhino repository.
Commit/push this repository before committing its gitlink in the parent.
`main` contains personal integration. The upstream `codex/undo-recovery` PR
remains limited to the existing Undo/Redo fix on `release/0.7.0rc2`.

- `src/mcp/almond_mcp`: upstream Python server, algorithms and library APIs.
- `src/engine`: user-made execution, storage/connection layer and Almond.Engine.dll.
- `src/cos`: user-made COS Python host/worker.
- `src/rhp/RhinoTerminal`, `src/rhp/AlmondCOS`: user-made Rhino plugins.
- `src/rhp/RhinoAlmondBridge`: upstream bridge project and core.
- `src/rhp/Structural_Analysis`, `src/rhp/Asset_Panel`: feature sources compiled
  into the same upstream bridge. The shared panel web resources stay together.

Folder classification does not change assemblies, GUIDs, namespaces, command
names, solver logic or tool schemas. Engine and MCP remain separate. The latest
reorganization permits path/packaging/reference changes in upstream files;
do not use that permission for functional refactors. Preserve the Undo patch.
Do not confuse Almond.Engine.dll with RhinoAlmondBridge.rhp or the parent's
unrelated `mcp/native` project. Never patch installed package files.

## Runtime and data

One editable environment lives at `src/engine/.venv`, reproduced by `uv.lock`.
Normal startup never syncs dependencies. Regenerate the COS catalog after source
path/source changes and retain its version, source-fingerprint and schema checks.
Local RHP outputs and dependencies belong under `src/rhp/<plugin>/plugin-build`.
The optional SDK is ignored at `src/rhp/RhinoTerminal/data/sdk`.

Preserve existing AppData libraries and explicit `RHINO_MCP_*_DIR` overrides.
The repository `asset/` tree, wheel `almond_mcp/data/` names and user AppData
names are different layouts. Do not rewrite upstream asset download URLs as
local paths. Preserve manifest-relative paths and byte/hash integrity.

A model folder shares `.almond/scene.sqlite3` and `.almond/tmp`. Each connection
owns its token/session/call directory. Preserve shared DB locks, role leases,
A-J slots, process identity, UI-thread checks and acknowledged native completion.
No session owns the entire DB. Timeout is not rollback; never retry an uncertain
mutation automatically. Finish/detach before moving or renaming a model.

Only delete user models/databases on explicit request. Put temporary development
artifacts in ignored local `data/`, never in a model's data. Do not retain redundant
Undo backups: the source fix is in Git and the installed RHP is separate.

## Verification and changes

Tests live in root `tests/engine`, `tests/mcp`, `tests/cos`, `tests/rhp`.
Keep source, tests, locks, licenses and useful docs. Exclude venvs, SDKs, binaries,
local config, sessions, user models and logs. Keep asset contracts/vendor hashes
and `.gitattributes` aligned when moving files. Preserve unrelated user changes.

Build success, registry configuration and live Rhino loading are separate evidence.
Never force-close a user's Rhino or overwrite loaded RHPs. An offline fixture is
not actual modeling, panel interaction, placement or structural analysis in Rhino.
Preserve Terminal UI/ConPTY/Ctrl behavior and all validation/error handling.

## Working style

- Respond in Korean. Inspect existing callers and make the smallest verified change.
- Keep a path-only reorganization free of functional changes and new abstractions.
- Ask only when an important unknown cannot be resolved locally.
- PowerShell and UTF-8 are defaults. Quote rg patterns/globs with single quotes.
- Validate absolute paths before recursive move/delete; use one shell end-to-end.
- Do not use SuperPower unless requested or message others without authorization.
- Legal notices required by included code/assets are not disposable clutter.
