# Rhino native module

Follow `../../AGENTS.md`. Keep native responsibilities and validation details in
`SPEC.md` and the owning component's instructions/tests, not the root SPEC.

Preserve plugin/assembly/command identities, Undo/Redo and observation contracts.
Shared Engine code belongs to `Engine`; COS plugin source belongs to `../cos/rhp`.
Keep existing installation output paths. Never overwrite a loaded runtime or
change everyday registration while developing another worktree.

Keep module tests out of production compile globs. Build with the actual Rhino 8
SDK. Source edits, output placement, registration and live loading are separate
evidence. Follow the Bridge native fixture README for disposable Rhino testing.
