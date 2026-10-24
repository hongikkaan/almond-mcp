# MCP execution runtime

Follow `../../../AGENTS.md` and `../AGENTS.md`. This folder owns the shared
Python execution entry point and CLI integration. Native `Almond.Engine.dll`
belongs to `../../rhp/Engine`; do not add native implementation here.

All entry points use the same editable environment. Keep per-folder DB/tmp,
per-token leases, A–J slots, process identity checks and native completion
tracking. No session exclusively owns the shared DB. Do not remove locks to
permit additional connections or retry uncertain native mutations.

Default library roots remain AppData; explicit overrides win. Call files belong
under the bound `artifact_dir`. Preserve original helper wrappers and validation.
Do not modify upstream package files to bypass a user-made integration failure.
