# RhinoTerminal checks

Run from the repository root with .NET 8 and Node.js. These fixtures do not open
Rhino or use a user model. Use the local SDK under `data/sdk` when needed.

```powershell
New-Item -ItemType Directory -Path data/terminal-tests -Force | Out-Null
dotnet run --project src/rhp/RhinoTerminal/tests/TerminalControls/TerminalControls.csproj
node --test src/rhp/RhinoTerminal/tests/terminal-web.test.mjs
dotnet run --project src/rhp/RhinoTerminal/tests/TerminalSmoke.csproj -- data/terminal-tests
dotnet run --project src/rhp/RhinoTerminal/tests/AlmondHostContracts/AlmondHostContracts.csproj -- data/terminal-tests
```

- TerminalControls compiles the production command, panel and runtime against
  Rhino/Eto/process doubles. It checks restored panels, hidden On/Off,
  PanelToggle, command cancellation, view disposal, output replay and shutdown.
- The Node fixture executes the embedded page script and checks exact shortcut
  input, ordinary keyboard input and disabled buttons during shell startup.
- TerminalSmoke starts disposable real ConPTY PowerShell shells and checks
  Unicode, resize, child containment, exit output and early stop.
- AlmondHostContracts uses production host and lease code with simulated Rhino
  and native work; it checks ownership and native drain behavior, attachment for
  a newly saved project without a temp folder, and rejection of foreign storage.

These are separate from a Bridge build and live Rhino validation. After building
the Bridge with Rhino closed, use a disposable document to verify that a restored
panel is stopped, all three command choices work with a hidden/visible panel,
and both shortcuts enter the expected command at a PowerShell prompt.
