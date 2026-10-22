namespace AlmondEngine;

/// <summary>New sessions share these handles; legacy FileShare.None owners exclude them in both directions.</summary>
public sealed class SharedStorageLease : IDisposable
{
    readonly List<FileStream> handles = new();

    public static SharedStorageLease Acquire(string storage) => new(storage);

    public SharedStorageLease(string storage)
    {
        SessionFiles.CheckPlainPath(storage);
        try
        {
            foreach (var name in new[] { "launcher.lock", "rhino.lock", "mcp.lock" })
            {
                var path = Path.Combine(storage, name);
                SessionFiles.CheckPlainPath(path);
                handles.Add(new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.ReadWrite));
            }
        }
        catch { Dispose(); throw; }
    }

    public void Dispose()
    {
        foreach (var handle in handles) handle.Dispose();
        handles.Clear();
    }
}
