# Rhino native module

Follow `../../AGENTS.md`. Keep native responsibilities and validation details in
`SPEC.md` and the owning component's instructions/tests, not the root SPEC.

Preserve plugin/assembly/command identities, Undo/Redo and observation contracts.
Shared Engine code belongs to `Engine`; AlmondRhino plugin source belongs to `../cos/rhp`.
Keep existing installation output paths. Never overwrite a loaded runtime or
change everyday registration while developing another worktree.

Keep module tests out of production compile globs. Build with the actual Rhino 8
SDK. Source edits, output placement, registration and live loading are separate
evidence. Follow the Bridge native fixture README for disposable Rhino testing.

Source edits and offline tests can run while Rhino is open. Only an RHP build/output replacement requires Rhino to be closed: check immediately before that step and ask the user to save and close normally if needed. Never force-close Rhino. Default tests use fixtures without starting or connecting to Rhino; fixture builds are not RHP builds. Live Rhino verification requires a separate user request.
