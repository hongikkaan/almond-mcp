param([string]$Script = (Join-Path $PSScriptRoot '../tests/check_model.py'))
$ErrorActionPreference = 'Stop'
$env:PATH = 'C:\Program Files\Rhino 8\System;' + $env:PATH
$psRuntime = Join-Path ([IO.Path]::GetTempPath()) 'PlanSection-runtime'
New-Item -ItemType Directory -Path $psRuntime -Force | Out-Null
$psHost = Join-Path $psRuntime 'native_check_host.exe'
if (-not (Test-Path -LiteralPath $psHost)) {
    Add-Type -ReferencedAssemblies 'C:/Program Files/Rhino 8/System/RhinoCommon.dll' -OutputAssembly $psHost -OutputType ConsoleApplication -TypeDefinition @'
using System;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
class NativeCheck {
    [STAThread] static int Main(string[] args) {
        AppDomain.CurrentDomain.AssemblyResolve += (s,e) => {
            var path = Path.Combine(@"C:\Program Files\Rhino 8\System", new AssemblyName(e.Name).Name+".dll");
            return File.Exists(path) ? Assembly.LoadFrom(path) : null;
        };
        try { return Run(args[0]); }
        catch (Exception error) {
            Console.Error.WriteLine(error.Message);
            return 1;
        }
    }
    [MethodImpl(MethodImplOptions.NoInlining)] static int Run(string path) {
        using (var core = new Rhino.Runtime.InProcess.RhinoCore()) {
            var engine = Rhino.Runtime.PythonScript.Create();
            return engine != null && engine.ExecuteFile(path) ? 0 : 1;
        }
    }
}
'@
}
& $psHost ([IO.Path]::GetFullPath($Script))
if ($LASTEXITCODE -ne 0) { throw 'Rhino Python execution failed' }
