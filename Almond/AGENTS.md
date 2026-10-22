# User-made Almond Engine

Follow `../AGENTS.md` and `../LOCAL_SETUP.md`. `_engine` owns the shared Python
entry point and `Almond.Engine.dll`; neither is the upstream bridge.

All entry points use the same editable environment. Keep per-folder DB/tmp,
per-token leases, A–J slots, process identity checks and native completion
tracking. No session exclusively owns the shared DB. Do not remove locks to
permit additional connections or retry uncertain native mutations.

Default library roots remain AppData; explicit overrides win. Call files belong
under the bound `artifact_dir`. Preserve original helper wrappers and validation.
Do not modify upstream package files to bypass a user-made integration failure.
