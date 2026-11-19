#nullable enable
using System;
using System.IO;
using AlmondEngine;

namespace RhinoAlmondBridge;

internal sealed record DashboardDocumentContext(string? DocumentPath, uint SerialNumber, string? DatabasePath, string Status)
{
    internal static DashboardDocumentContext Resolve(string? modelPath, uint serialNumber)
    {
        if (string.IsNullOrWhiteSpace(modelPath))
            return new(null, serialNumber, null, "현재 Rhino 문서를 먼저 저장하세요. 이전 프로젝트 DB는 표시하지 않습니다.");
        try
        {
            // Reuse the same saved-document → project storage contract as
            // AlmondHost/RhinoHost. create:false does not allocate a session,
            // take a slot/lease, create directories, or initialize a database.
            var paths = SessionFiles.Paths(modelPath, "A", new string('0', 32), create: false);
            string database = paths.StateDb;
            if (!File.Exists(database))
                return new(paths.ModelPath, serialNumber, null, "현재 문서 프로젝트에 기존 DB가 없습니다: " + paths.ModelPath);
            if ((File.GetAttributes(database) & FileAttributes.ReparsePoint) != 0)
                throw new IOException("DB 파일 링크는 자동 선택하지 않습니다.");
            // An existing DB can be read without an MCP connection. Validate
            // access only; the existing Python viewer validates SQLite format.
            using (new FileStream(database, FileMode.Open, FileAccess.Read,
                FileShare.ReadWrite | FileShare.Delete)) { }
            return new(paths.ModelPath, serialNumber, database, "Rhino 문서: " + paths.ModelPath + " · 자동 선택 기준 DB: " + database);
        }
        catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException || ex is ArgumentException || ex is NotSupportedException)
        {
            return new(modelPath, serialNumber, null, "현재 문서의 DB를 선택하지 못했습니다: " + modelPath + " · " + ex.Message);
        }
    }
}

internal sealed class DashboardDocumentSession : IDisposable
{
    readonly Func<string, DashboardRuntime> create;
    internal DashboardDocumentContext? Context { get; private set; }
    internal DashboardRuntime? Runtime { get; private set; }

    internal DashboardDocumentSession(Func<string, DashboardRuntime> create) => this.create = create;

    internal DashboardDocumentContext Select(string? modelPath, uint serialNumber, bool reselect = false)
    {
        var next = DashboardDocumentContext.Resolve(modelPath, serialNumber);
        if (reselect || next.DatabasePath == null || Context?.DatabasePath == null ||
            !SessionFiles.Same(next.DatabasePath, Context.DatabasePath))
        {
            Runtime?.Dispose();
            Runtime = null;
            if (next.DatabasePath != null) Runtime = create(next.DatabasePath);
        }
        Context = next;
        return next;
    }

    public void Dispose() { Runtime?.Dispose(); Runtime = null; Context = null; }
}
