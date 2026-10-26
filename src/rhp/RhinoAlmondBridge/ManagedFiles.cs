using System;
using System.IO;
using System.Threading;
using Rhino;

namespace RhinoAlmondBridge
{
    /// <summary>Call-scoped relative IO, without changing Rhino's process cwd.</summary>
    public static class ManagedFiles
    {
        private sealed class Context { public string Root; public string Artifact; }
        private static readonly AsyncLocal<Context> Current = new AsyncLocal<Context>();

        public static IDisposable Bind(RhinoDoc doc, string root, string artifact)
        {
            var previous = Current.Value;
            if (string.IsNullOrWhiteSpace(root))
                Current.Value = null;
            else
            {
                if (doc == null || string.IsNullOrWhiteSpace(doc.Path) ||
                    !string.Equals(Path.GetFullPath(root).TrimEnd('\\'), Path.GetDirectoryName(Path.GetFullPath(doc.Path)), StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Managed project root does not match the current saved document.");
                Current.Value = new Context { Root = Path.GetFullPath(root), Artifact = artifact ?? "" };
            }
            return new Scope(() => Current.Value = previous);
        }

        public static string Input(string relativePath)
        {
            var context = Current.Value ?? throw new InvalidOperationException("No active managed file scope.");
            return Resolve(context.Root, relativePath);
        }

        public static string Output(string relativePath)
        {
            var context = Current.Value ?? throw new InvalidOperationException("No active managed file scope.");
            if (context.Artifact.Length == 0)
                throw new InvalidOperationException("Select a Plan with set_working_plan before writing artifacts.");
            var root = Resolve(context.Root, context.Artifact);
            var path = Resolve(root, relativePath);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            return path;
        }

        private static string Resolve(string root, string relative)
        {
            if (string.IsNullOrWhiteSpace(relative) || Path.IsPathRooted(relative) || relative.Contains(":"))
                throw new ArgumentException("Use a relative path inside the managed folder.");
            foreach (var part in relative.Split('\\', '/'))
                if (part == "..") throw new ArgumentException("Managed paths cannot escape their folder.");
            var path = Path.GetFullPath(Path.Combine(root, relative));
            var prefix = Path.GetFullPath(root).TrimEnd('\\', '/') + Path.DirectorySeparatorChar;
            if (!path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("The managed path must name a file inside its folder.");
            for (var current = path; current != null; current = Path.GetDirectoryName(current))
            {
                if ((File.Exists(current) || Directory.Exists(current)) && (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                    throw new IOException("Managed paths cannot traverse filesystem links.");
                if (string.Equals(current, root, StringComparison.OrdinalIgnoreCase)) break;
            }
            return path;
        }

        private sealed class Scope : IDisposable
        {
            private Action close;
            public Scope(Action action) { close = action; }
            public void Dispose() { var action = close; close = null; action?.Invoke(); }
        }
    }
}
