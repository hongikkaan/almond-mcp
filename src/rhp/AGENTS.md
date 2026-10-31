# Rhino native module

Follow `../../AGENTS.md`. Keep native responsibilities and validation details in `SPEC.md` and the owning component's instructions/tests, not the root SPEC.

Preserve plugin/assembly/command identities, Undo/Redo and observation contracts.
Shared Engine code belongs to `Engine`; AlmondRhino plugin source belongs to `../cos/rhp`.
Keep installation output paths stable after migration. The explicit AlmondCOS to AlmondRhino migration requires the one-time backed-up registration step in the root README/AGENTS after pull and before restarting Rhino; pull alone does not update an old PlugIn\\FileName. Never overwrite a loaded runtime or change everyday registration while developing another worktree.

Keep module tests out of production compile globs. Build with the actual Rhino 8 SDK. Source edits, output placement, registration and live loading are separate evidence. Test live functionality in the Rhino files the user connected for the task; avoid creating or launching separate Rhino documents solely for tests.
The Bridge native fixture README describes fixture-specific prerequisites, not a default instruction to start another Rhino. Never remove a fixture's document guards or run a fixture that replaces document contents in a user model.

Source edits and offline tests can run while Rhino is open. Only an RHP build/output replacement requires Rhino to be closed: check immediately before that step and ask the user to save and close normally if needed. Never force-close Rhino. Offline unit and integration tests run without starting or connecting to Rhino; fixture builds are not RHP builds. When live verification is part of the user's task, use their connected working files and preserve their model and document state.

## Shared Engine

Own native transport completion, connection identity and shared storage leases. Depend on platform/Rhino APIs, never on either host.
Both Bridge and AlmondRhino consume this assembly. Keep their shipped DLLs identical after an Engine change and run the local native fixtures plus host integrations.
Do not add Python MCP or COS adapter policy here.

## RhinoTerminal

The panel's `almond` command reuses the common Engine and editable environment.
Keep current document identity, leases and native drain checks. Integration maintenance must preserve shell/ConPTY/Ctrl behavior and terminal UI.
Keep all plugin dependencies together and distinguish registered from loaded versions. Do not force-close a user's Rhino or replace its loaded assembly.
