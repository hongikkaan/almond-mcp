using System;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino.Display;

namespace RhinoAlmondBridge
{
    internal static class DisplayModeMenu
    {
        private static DisplayModeDescription[] GetModes() =>
            DisplayModeDescription.GetDisplayModes().Where(mode => mode.InMenu).ToArray();

        internal static JArray List(JArray warnings)
        {
            var modes = GetModes();
            if (modes.Length > 128)
                warnings.Add("display_modes: first 128 modes from the View Display Mode Menu returned.");
            return new JArray(modes.Take(128).Select(mode => new JObject
                { ["name"] = mode.EnglishName, ["id"] = mode.Id.ToString() }));
        }

        internal static DisplayModeDescription Resolve(string value)
        {
            var modes = GetModes();
            if (Guid.TryParse(value, out var id))
                return modes.FirstOrDefault(mode => mode.Id == id);
            var matches = modes.Where(mode =>
                String.Equals(mode.EnglishName, value, StringComparison.OrdinalIgnoreCase) ||
                String.Equals(mode.LocalName, value, StringComparison.OrdinalIgnoreCase)).ToArray();
            return matches.Length == 1 ? matches[0] : null;
        }

        internal static void VerifyApplied(RhinoViewport viewport, DisplayModeDescription mode)
        {
            if (viewport.DisplayMode?.Id != mode.Id)
                throw new InvalidOperationException("The viewport did not apply the requested display mode.");
        }
    }
}
