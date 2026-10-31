# Offline checks

Run from the checkout root after preparing its independent development environment:

```powershell
./src/mcp/run_tests.ps1 -Development
./src/cos/run_tests.ps1 -Development
./tests/run_tests.ps1 -Development
& ./data/development/.venv/Scripts/python.exe -B tests/verify_library_sources.py
```

If .NET SDK discovery fails, pass `-DotNet <SDK/dotnet.exe>` to the runners. The
root runner prepares ArchiveHost; selecting its tests directly requires an absolute
`ALMOND_ARCHIVE_TEST_HOST` executable path and fails explicitly if it is missing.

The stdio tests start the real Python MCP service in child processes, with empty
temporary library directories and a disposable database. The bound fixture calls
`mcp_server.serve` with an empty placeholder model and synthetic binding metadata;
it never opens the placeholder in Rhino or calls a native modeling tool. It checks
the wire-level initialize instructions, all public descriptions and full explicit
guides, and compares actual worker schemas with a fixed baseline and both beyond
and CoS stdio catalogs. The baseline must be deliberately reviewed when a public
schema changes. A packaging test builds a wheel with `uv build --offline` and
therefore requires the build dependencies in the local uv cache.

`verify_library_sources.py` verifies shipped generated assets against their
manifest hashes and provenance records. It does not inspect installed AppData
libraries, exercise live Rhino, prove plugin registration or loading, or validate
all possible model workflows. Passing these tests is not a substitute for a real
feature test in the user's connected model.

The rebuilt suite does not yet cover all former modeling/calculation cases,
native Undo/Redo, live viewport observation, ConPTY UI behavior, or RhinoHost
lifecycle. Missing coverage is not a passing result. Do not run document-resetting
fixtures in a user's working model to fill those gaps.

The installed CLI launcher check is an explicit, separate check:

```powershell
./src/mcp/tests/runtime/test_terminal_launch.ps1 -Codex <installed-codex.exe>
```

The launch check runs the actual CLI config resolver, doubles only OS binding
observations, and intercepts the interactive launch. It does not prove a live
RhinoTerminal session's roster. It does not change user settings, installed Codex,
or any live Rhino connection.
