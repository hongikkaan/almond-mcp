# Compatibility entry points

This directory is not an implementation module. MCP execution and launch codeis owned by `../mcp/runtime`; the native Engine is owned by `../rhp/Engine`.

The existing start/cleanup buttons and installation commands forward to their owners. `.venv` remains here because existing CoS command registrations point at its Python executable. Each checkout creates its own environment; do not copy or share it. Existing ignored `data` is retained, never migrated or deleted automatically. New connection records are owned by `../mcp/runtime/data`.

Do not add business logic here. A future removal of these compatibility paths requires an explicit installation migration.

`rebuild_environment.ps1` forwards to MCP maintenance. Its default repairs the daily environment and an existing root `.venv`, then configures CoS. `-VerifyOnly` checks both environments without installing packages or configuring CoS. `-Development` forwards only to the separate development environment. The implementation and usage are owned by `../mcp/rebuild_environment.ps1` and the root README.
