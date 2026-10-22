# Personal Almond fork

## Repository and ownership

This checkout is the `mcp/almond-mcp` submodule of the local Rhino repository.
Commit/push source changes here first, then commit its gitlink in the parent.
`main` is the personal integration branch. `codex/undo-recovery` and upstream
PR #39 contain only the single Undo/Redo fix on `release/0.7.0rc2`.

| Component | Owner and role |
|---|---|
| `almond_mcp` | Upstream Python MCP server, executed from this editable checkout |
| `RhinoAlmondBridge` | Upstream Rhino plugin, with the existing Undo/Redo patch |
| `Almond/_engine` | User-made launcher, shared storage and `Almond.Engine.dll` transport |
| `AlmondCOS` | User-made COS stdio host/workers and Rhino RHP |
| `RhinoTerminal` | User-made Rhino terminal and connection to the shared Engine |

Keep general integration fixes in the three user-made components. Do not edit
installed upstream package files or bypass integration bugs by changing upstream
server/bridge implementation. The existing Undo/Redo patch is the narrow source
exception; dependency metadata/lock changes for this personal fork are allowed.
Do not confuse `Almond.Engine.dll` with upstream `RhinoAlmondBridge.rhp` or the
parent workspace's unrelated `mcp/native` component.

## Runtime and data

Follow `LOCAL_SETUP.md`. One Python 3.12.12 environment lives at
`Almond/_engine/.venv`; `uv.lock` and local/dev groups reproduce dependencies.
The project is installed editable. Normal startup does not sync dependencies.
Source/schema changes require reviewed COS catalog regeneration and new workers.
Do not disable version, source-fingerprint or tool-schema checks.

Model-folder `.almond/scene.sqlite3` and `.almond/tmp` are shared by models in
that folder. Each connection owns a new `.sessions/<token>` and call root.
Preserve shared DB locks, role leases, A–J slots, PID/start identity, UI-entry
checks and acknowledged native completion. No session exclusively owns the DB.
Timeout/EOF is not rollback; do not replay uncertain mutations automatically.

Default libraries remain in AppData; explicit `RHINO_MCP_*_DIR` overrides win.
Preserve release-specific paths and compare Python paths with native caches.
Do not copy libraries/models/databases into Git or change their location just
because the Python source moved. Task artifacts belong in the bound artifact_dir;
repository development fixtures belong in ignored project-local `data/`.

Finish/detach before model switching, Save As, renaming or moving. Do not reset
or delete user models/databases without an explicit request. Historical Undo
backup folders are not runtime requirements: the fix is in Git and the installed
RHP is separate. Do not create or retain redundant backups by default.

## Build, verification and installation

`RhinoTerminal/data/sdk` is the optional local .NET SDK, ignored by Git. A .NET 8
SDK on PATH also works. RHP outputs stay directly under each project, alongside
all dependencies. Build success, registered paths and live loaded assembly/MVID
are separate evidence. Never replace a loaded RHP or force-close a user's Rhino.
Keep the installed upstream Undo-patched bridge unless explicitly changing it.

Use the environment Python for Engine unit tests and library-routing probes;
`AlmondCOS/run_tests.ps1` covers native/host/pipe/stdio fixtures. Terminal host
checks use `dotnet run --project RhinoTerminal/tests/AlmondHostContracts -c Release
-- <absolute-existing-data-directory>`. Preserve unrelated Terminal UI/ConPTY/Ctrl
behavior. Distinguish isolated fixtures from real Rhino model execution.

Track source, tests, dependency locks, licenses and current docs only. Exclude
venvs, SDKs, binaries, local COS config, models, sessions and private logs. Do not
import the parent's history or unrelated changes. Keep the dedicated PR branch
free of personal integration commits.

## Working style

- Respond in Korean. Inspect callers and existing code before changing it; make
  the smallest complete change and verify material regression risks.
- State evidence, assumptions and actual verification limits. Ask only when a
  consequential unknown cannot be discovered locally.
- PowerShell is the default shell. Use UTF-8, single-quoted rg patterns/globs,
  check native exit codes, and avoid cross-shell destructive commands.
- Before recursive delete/move, verify exact absolute paths and scope. Preserve
  unrelated work. Do not send Slack/email updates without explicit authorization.
- Do not use SuperPower unless requested. No deployment/publishing machinery is
  needed for this personal-use checkout.
