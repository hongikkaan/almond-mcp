using System.Diagnostics;
using System.Net;
using System.Runtime.InteropServices;

namespace AlmondEngine;

internal readonly record struct WorkerIdentity(int Pid, string StartTicks)
{
    internal bool IsAlive()
    {
        try
        {
            using var process = Process.GetProcessById(Pid);
            return !process.HasExited && process.StartTime.ToUniversalTime().Ticks.ToString() == StartTicks;
        }
        catch (ArgumentException) { return false; }
        catch (InvalidOperationException) { return false; }
        catch (System.ComponentModel.Win32Exception) { return false; }
    }
}

internal static class WindowsPeerIdentity
{
    [StructLayout(LayoutKind.Sequential)]
    struct TcpRow { internal uint state, localAddress, localPort, remoteAddress, remotePort, ownerPid; }

    [DllImport("iphlpapi.dll", SetLastError = true)]
    static extern uint GetExtendedTcpTable(IntPtr table, ref int size, bool order, int family, int tableClass, uint reserved);

    static int Port(uint value) => (int)(((value & 255) << 8) | ((value >> 8) & 255));

    internal static bool Matches(IPEndPoint peer, int serverPort, WorkerIdentity worker)
    {
        if (!IPAddress.IsLoopback(peer.Address) || !worker.IsAlive()) return false;
        int size = 0;
        var result = GetExtendedTcpTable(IntPtr.Zero, ref size, false, 2, 5, 0);
        if (result != 122) throw new IOException("Cannot read TCP client ownership.");
        for (int retry = 0; retry < 3; retry++)
        {
            var buffer = Marshal.AllocHGlobal(size);
            try
            {
                result = GetExtendedTcpTable(buffer, ref size, false, 2, 5, 0);
                if (result == 122) continue;
                if (result != 0) throw new IOException("Cannot read TCP client ownership.");
                int count = Marshal.ReadInt32(buffer), stride = Marshal.SizeOf<TcpRow>();
                if (count < 0 || 4L + (long)count * stride > size)
                    throw new IOException("Invalid TCP client ownership table.");
                for (int i = 0; i < count; i++)
                {
                    var row = Marshal.PtrToStructure<TcpRow>(IntPtr.Add(buffer, 4 + i * stride));
                    // This is the client's row: local port is the accepted socket's peer port.
                    if (row.state == 5 && row.localAddress == 0x0100007f && row.remoteAddress == 0x0100007f &&
                        Port(row.localPort) == peer.Port && Port(row.remotePort) == serverPort &&
                        row.ownerPid == worker.Pid) return true;
                }
                return false;
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }
        throw new IOException("TCP client ownership table kept changing.");
    }
}
