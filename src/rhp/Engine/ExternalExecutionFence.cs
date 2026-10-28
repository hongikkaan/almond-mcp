using System.ComponentModel;
using System.Diagnostics;
using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace AlmondEngine;

/// <summary>Retains session ownership while official CLI work can still execute.</summary>
internal static class ExternalExecutionFence
{
    static readonly Regex Token = new(@"\A[0-9a-f]{32}\z", RegexOptions.CultureInvariant);
    static readonly Regex Hash = new(@"\A[0-9a-f]{64}\z", RegexOptions.CultureInvariant);

    internal static bool IsPending(SessionPaths paths, string token, int pid, string startTicks, uint serial)
    {
        JsonDocument journal;
        try { journal = SessionFiles.ReadJson(paths.RhinocodePath); }
        catch (FileNotFoundException) { return false; }
        catch (DirectoryNotFoundException) { return false; }
        catch { return true; }
        using (journal)
        {
            try
            {
                var value = journal.RootElement;
                if (!Header(value, "almond-rhinocode-execution") || Text(value, "token") != token)
                    return true;
                var operation = Text(value, "operation_id");
                var request = Text(value, "request_id");
                var nonce = Text(value, "nonce");
                var sourceHash = Text(value, "source_hash");
                if (!Token.IsMatch(operation) || !Token.IsMatch(request) || !Token.IsMatch(nonce) || !Hash.IsMatch(sourceHash))
                    return true;
                if (Text(value, "language") is not ("python" or "python2" or "csharp-script" or "command")) return true;
                var target = value.GetProperty("target");
                if (!TargetMatches(target, paths.ModelPath, pid, startTicks, serial)) return true;
                bool compact = value.TryGetProperty("layout", out var layout);
                if (compact && (layout.ValueKind != JsonValueKind.String || layout.GetString() != "compact-v1")) return true;
                // Only a positively recorded failure before Popen can omit its child.
                if (value.TryGetProperty("not_dispatched", out var notDispatched) && notDispatched.ValueKind == JsonValueKind.True)
                    return !value.TryGetProperty("child", out var absentChild) || absentChild.ValueKind != JsonValueKind.Null ||
                        Text(value, "dispatch_error").Length == 0;
                var child = value.GetProperty("child");
                if (child.ValueKind != JsonValueKind.Object || !Exited(child)) return true;
                var directory = compact ? Path.Combine(paths.CallRoot, operation, "rc-" + request[..12]) :
                    Path.Combine(paths.CallRoot, operation, "rhinocode", request);
                SessionFiles.CheckPlainPath(directory);
                var finalPath = Path.Combine(directory, "complete.json");
                if (new FileInfo(finalPath).Length > 65536) return true;
                using var final = SessionFiles.ReadJson(finalPath);
                var receipt = final.RootElement;
                if (!Header(receipt, "almond-rhinocode-completion") ||
                    !receipt.TryGetProperty("execution_complete", out var complete) || complete.ValueKind != JsonValueKind.True ||
                    Text(receipt, "status") is not ("success" or "error" or "rejected") ||
                    Text(receipt, "mutation_state") is not ("completed" or "partial" or "not_started" or "unknown"))
                    return true;
                foreach (var key in new[] { "token", "operation_id", "request_id", "nonce", "source_hash" })
                    if (Text(receipt, key) != Text(value, key)) return true;
                bool receiptCompact = receipt.TryGetProperty("layout", out var receiptLayout);
                if (compact != receiptCompact || (compact &&
                    (receiptLayout.ValueKind != JsonValueKind.String || receiptLayout.GetString() != "compact-v1"))) return true;
                var actual = receipt.GetProperty("target");
                if (!TargetMatches(actual, paths.ModelPath, pid, startTicks, serial) ||
                    Text(actual, "pipe_id") != Text(target, "pipe_id")) return true;
                return false;
            }
            catch { return true; }
        }
    }

    static bool Header(JsonElement value, string schema) =>
        value.ValueKind == JsonValueKind.Object && Text(value, "schema") == schema &&
        value.TryGetProperty("version", out var version) && version.TryGetInt32(out var number) && number == 1;

    static string Text(JsonElement value, string key) =>
        value.TryGetProperty(key, out var property) && property.ValueKind == JsonValueKind.String
            ? property.GetString() ?? "" : "";

    static bool TargetMatches(JsonElement target, string model, int pid, string ticks, uint serial) =>
        target.ValueKind == JsonValueKind.Object && target.GetProperty("pid").TryGetInt32(out int actualPid) &&
        actualPid == pid && Text(target, "process_start_ticks") == ticks &&
        target.GetProperty("document_serial").TryGetUInt32(out uint actualSerial) && actualSerial == serial &&
        Text(target, "model_path").Length != 0 && SessionFiles.Same(Text(target, "model_path"), model) &&
        Text(target, "pipe_id").Length != 0;

    static bool Exited(JsonElement identity)
    {
        var text = Text(identity, "process_start_ticks");
        if (!identity.GetProperty("pid").TryGetInt32(out int pid) || pid <= 0 ||
            !long.TryParse(text, NumberStyles.None, CultureInfo.InvariantCulture, out long ticks) || ticks <= 0 ||
            text != ticks.ToString(CultureInfo.InvariantCulture))
            return false;
        try
        {
            using var process = Process.GetProcessById(pid);
            return process.HasExited || process.StartTime.ToUniversalTime().Ticks != ticks;
        }
        catch (ArgumentException) { return true; }
        catch (InvalidOperationException) { return true; }
        catch (Win32Exception) { return false; } // Inaccessible is not exited.
    }
}
