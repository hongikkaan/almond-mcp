# Building RhinoAlmondBridge

This personal fork compiles the Bridge, Structural_Analysis, Asset_Panel and
RhinoTerminal into one `net8.0-windows` RHP. Engine remains a separate DLL and
Python environment; AlmondCOS remains a separate plugin.

## Prerequisites

1. .NET 8 SDK, either on PATH or in `src/rhp/RhinoTerminal/data/sdk`.
2. Rhino 8 for Windows, running .NET 8. The integrated build was verified with
   Rhino 8.34. RhinoCommon, Rhino.UI, Eto, Grasshopper and GH_IO are referenced
   from the installed Rhino SDK and are not copied into the package.
3. Karamba3D 3.1 (build 3.1.60519) installed for Rhino 8. Optional at build time, required at runtime for the "api" analysis path.
4. The prepared `src/engine/.venv` from [local setup](../../../LOCAL_SETUP.md).
   Initial dependency/bootstrap downloads need Internet access. NuGet dependencies
   include Roslyn, Newtonsoft.Json and Porta.Pty; their versions are locked.

## Build steps

Run from the repository root:

```powershell
./src/rhp/build.ps1
```

The complete output is `src/rhp/RhinoAlmondBridge/plugin-build`. Keep
`RhinoAlmondBridge.rhp`, Almond.Engine/Porta.Pty/Vanara/Roslyn/Newtonsoft DLLs,
deps/runtimeconfig JSON, `licenses` and `archive` together. The build checks for
loaded output files, builds into a fresh staging directory, then swaps the output.
It does not install, register or launch Rhino. Close a Rhino using that output
normally before rebuilding it.

Terminal resolves `../../../engine` from the assembly directory. Preserve the
`RhinoAlmondBridge/plugin-*` output depth; moving only an RHP is insufficient.
For an isolated package build, use `tools/build_yak.ps1` with explicit Python and
dotnet executable paths as shown in [local setup](../../../LOCAL_SETUP.md).
The Yak tag follows the referenced Rhino SDK, currently `rh8_34-win`; it is
verified before copying to `dist/yak` and is not published automatically.

The project intentionally has NO reference to any Karamba assembly. Do not add one. All Karamba access is late bound through reflection inside `KarambaAdapter.cs`, so the plugin compiles and runs on machines without Karamba and simply reports the api path as unavailable there.

## Where the Karamba 3.1 DLLs live

The Karamba installer for Rhino 8 places its assemblies in the Rhino plugin folder:

```
C:\Program Files\Rhino 8\Plug-ins\Karamba\
    karambaCommon.dll     (the API the adapter binds to)
    Karamba.dll           (loaded when present)
    Karamba.gha           (Grasshopper components, not used by the adapter)
```

If Karamba was installed through the Rhino package manager instead, the files live under:

```
%APPDATA%\McNeel\Rhinoceros\packages\8.0\Karamba3D\<version>\
```

## How the adapter resolves Karamba at runtime

`KarambaAdapter` probes in this order and stops at the first hit:

1. `KarambaAdapter.OverridePluginPath` when set from code.
2. The `ALMOND_KARAMBA_DIR` environment variable when set.
3. `C:\Program Files\Rhino 8\Plug-ins\Karamba` and `...\Karamba3D`.
4. The yak package folders under `%APPDATA%\McNeel\Rhinoceros\packages\8.0`.
5. Before all of that, if the Karamba Grasshopper plugin already loaded `karambaCommon` into the process, that loaded assembly is reused directly.

A hit means a folder containing `karambaCommon.dll`. The adapter calls `Assembly.LoadFrom` on it, hooks `AssemblyResolve` so Karamba's own dependencies resolve from the same folder, and then drives everything through `KarambaCommon.Toolkit` via reflection. If no folder is found, every analysis request degrades to the template capsule path, then to the rule based estimate, and the failure reason (`api_unavailable: ...`) appears in the response warnings. Nothing throws.

If your Karamba sits somewhere unusual, set the environment variable before starting Rhino:

```
setx ALMOND_KARAMBA_DIR "D:\Tools\Karamba"
```

## What to check in the Rhino command line on first load

1. Start Rhino 8 with .NET 8 and register the complete local output through
   `PlugInManager`, using `RhinoAlmondBridge.rhp` and the existing Bridge GUID
   `c337dbb8-394a-4593-9c2b-a3d7cfc91893`. Remove the obsolete standalone Terminal
   registration after backing it up. Restart normally and verify the loaded path.
2. Expect these lines:
   ```
   RhinoAlmondBridge: Loading MCP Bridge plugin...
   RhinoAlmondBridge: TCP listener started on port 5000.
   RhinoAlmondBridge: Ready to receive C# scripts from MCP server.
   ```
3. If port 5000 is taken you will instead see `Failed to bind port 5000`. Identify
   the owning Rhino before changing anything; do not force-close a user's session.
4. Run `AlmondMCPStatus` to confirm the bridge is listening.
5. To confirm the Karamba api path, send a `validate` request (or use the MCP `validate_structure` tool) against a simple line and check the verdict prefix:
   `[KARAMBA 3.1 API, HIGH CONFIDENCE]` means the direct API worked.
   `[AUDITED TEMPLATE, MEDIUM CONFIDENCE]` means the API was unavailable but an audited capsule ran.
   `[RULE-BASED ESTIMATE, LOW CONFIDENCE]` means both were unavailable; check the `warnings` array in the response for the `api_unavailable` reason, which lists every folder that was probed.

## Directory expectations at runtime

The bridge locates support folders by walking up from the plugin DLL, with environment variable overrides:

| Purpose | Env override | Default search |
|---|---|---|
| GHX library | `RHINO_MCP_LIBRARY_DIR` | checkout `asset/grasshopper/Grasshopperfiles`, then AppData |
| Capsule manifests | `RHINO_MCP_CAPSULE_DIR` | checkout `asset/capsules`, then AppData |
| Karamba DLLs | `ALMOND_KARAMBA_DIR` | standard Rhino 8 Karamba locations above |

Manifest-relative paths and hashes are preserved under `asset/capsules`.
The personal Engine defaults to the existing AppData libraries. Before loading
the checkout build, ensure Bridge and Engine resolve the same `RHINO_MCP_*_DIR`
locations, preserving every explicit override and the existing user data.
