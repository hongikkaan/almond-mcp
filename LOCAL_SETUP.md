# Personal Rhino setup

This fork runs Almond 0.7.0rc2 from source and keeps the existing user-made
Engine, COS adapter and RhinoTerminal together. The upstream bridge retains
the Undo/Redo fix. No package publishing or automatic update service is used.

## Environment

Run `Almond/_engine/rebuild_environment.ps1` with all hosts/workers using this
checkout stopped. It uses Python 3.12.12, `uv.lock`, and the `local`/`dev`
dependency groups, installs this project editable into `Almond/_engine/.venv`,
checks dependency/source paths, and regenerates the COS catalog and ignored
`AlmondCOS/cos-plugin.json` for this checkout's absolute location.

Normal launchers invoke that Python directly; they do not sync packages during
a modeling session. Do not run an unrestricted `uv sync` against another
environment. To use uv commands manually set `UV_PROJECT_ENVIRONMENT` to this
checkout's `Almond/_engine/.venv` for that shell only. `uv run --no-sync` avoids
changing the environment during a session. `uv.lock` is the dependency source
of truth; the old requirements file is not used.

Editable Python changes require restarting the affected host/workers. After
reviewing source/schema changes regenerate `AlmondCOS/tool_catalog.json` with
the same Python. Do not bypass its version, source, or schema checks.

## Rhino and entry points

Keep the installed upstream `RhinoAlmondBridge.rhp` with its Undo/Redo patch.
Python setup neither builds nor installs that bridge. Build user-made plugins
with a .NET 8 SDK (`dotnet` on PATH):

```powershell
./AlmondCOS/build.ps1 -OutputDirectory "$PWD/AlmondCOS/plugin-build"
./RhinoTerminal/build.ps1 -OutputDirectory plugin-build
```

Register each resulting RHP in Rhino, keeping its dependencies next to it.
These plugin directories must stay directly under their project directories
because they locate `../Almond/_engine` relative to the assembly. Restart Rhino
normally to load newly registered versions; do not replace a loaded RHP.

- COS: use the generated `AlmondCOS/cos-plugin.json` command/args and 600-second
  limit. Restart that COS server, run `AlmondCOS` in a saved Rhino document,
  then select its exact host/model connection.
- Terminal: run `RhinoTerminal`, then `almond`. `/exit` detaches; use
  `almond resume` to resume through the binding workflow.
- External: `Almond/Almond 시작.cmd` selects an existing saved model and uses
  the same Engine. Build `Almond/_engine/native/Almond.Engine.csproj` Release
  for this entry point as well.

The old sibling installations are not needed. Do not copy or move an existing
venv; recreate one at its final path. The optional SDK is kept only in the ignored
`RhinoTerminal/data/sdk` directory; no parent build-tools directory is required.

## Data and library invariants

`library_paths.py` keeps default libraries in `%LOCALAPPDATA%/Almond`; generated
and drafting assets retain `releases/0.7.0rc2`. Explicit `RHINO_MCP_*_DIR`
overrides win. The original resolver still performs final lookup. Native helper
cached paths must match; restart Rhino with the same override configuration
when changing libraries. Source checkout libraries must not silently replace
existing user assets.

Saved models in one folder share `.almond/scene.sqlite3` and `.almond/tmp`.
Each connection owns `.sessions/<token>` and `tmp/calls/<token>`. Store locking,
UI-thread document checks, native completion acknowledgements, and uncertain
operation quarantine remain intact. A timeout is not a rollback. Finish and
detach before switching, moving, renaming or saving a document under a new path.

## Verification

Use the environment Python for `unittest discover -s Almond/_engine`,
`Almond/_engine/verify_library_sources.py`, and `AlmondCOS/run_tests.ps1`.
`RhinoTerminal/tests/AlmondHostContracts` checks its host separately.
Tests use disposable project-local fixtures. Real Rhino loading/model execution
must be reported separately from builds, isolated tests and registration.

Before publishing commits, inspect staged paths for sessions, models, binaries,
SDKs and local configuration. Only `main` receives personal integration changes;
the dedicated upstream PR branch remains limited to Undo/Redo.

This checkout is a Git submodule of the local Rhino repository. After updating
and pushing this repository, commit its gitlink in the parent repository. A fresh
parent checkout uses `git submodule update --init --recursive`. The submodule's
tracked `main` branch does not override the exact commit pinned by the parent.
