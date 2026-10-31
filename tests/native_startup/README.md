# Native startup and command contract

This offline fixture compiles the production Bridge and connection plugin entry points against inert Rhino/host doubles. It verifies startup does not open the legacy unbound transport, retains panels and the native handler, exposes only `almondconnect` / `almonddisconnect`, reuses discovery on repeated connect, and routes disconnect through existing safe cleanup. If the removed Commands.cs is reintroduced, its commands are automatically included in the catalogue check.

After building both RHPs, the optional arguments inspect their actual PE metadata without loading Rhino. This verifies the shipped command names, absence of the legacy transport, and initialization of every helper field used by Engine.

From the repository root, using an installed .NET 8 SDK:

```powershell
dotnet run --project tests/native_startup/NativeStartup.csproj -c Release -- src/rhp/RhinoAlmondBridge/plugin-runtime/RhinoAlmondBridge.rhp src/rhp/AlmondRhino/plugin-runtime/AlmondRhino.rhp
```

Host drain, worker ownership and independent sessions remain covered by `src/cos/tests/HostLifecycle` and `src/rhp/Engine/tests`. None of these fixtures is proof of loading the updated RHP in a real Rhino process.
