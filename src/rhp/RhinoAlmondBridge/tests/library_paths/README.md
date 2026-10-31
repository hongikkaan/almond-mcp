# Library startup contract

`verify.ps1` constructs the managed `BridgeServer` helpers from the shipped RHP, runs the actual Python worker library configuration, and invokes the shipped Engine's `NativeLibraryRoots.Validate` with those actual caches. It covers absent, empty, and explicit library overrides, and verifies that a changed worker root is still rejected without rewriting the native cache.

This test does not start Rhino, register a plugin, read a model, or execute native geometry. RhinoCommon is loaded only as a managed dependency. PowerShell 7, the installed Rhino SDK, the built runtime bundle, and this checkout's Python environment are required. Root integration tests run it automatically.

```powershell
./src/rhp/RhinoAlmondBridge/tests/library_paths/verify.ps1 `
  -RepositoryRoot (Get-Location).Path `
  -PythonExecutable ./data/development/.venv/Scripts/python.exe
```
