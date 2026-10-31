using System;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Commands;
using Rhino.Geometry;
using Rhino.Input;
using Rhino.Input.Custom;

namespace RhinoAlmondBridge
{
    internal static class LibraryPlacement
    {
        [DllImport("user32.dll")] private static extern bool ReleaseCapture();
        [DllImport("user32.dll")] private static extern short GetAsyncKeyState(int key);
        private static bool LeftDown => (GetAsyncKeyState(1) & 0x8000) != 0;
        internal static string PendingId;
        internal static bool PendingDrag;
        internal static bool PendingLight;
        internal static bool Busy;

        internal static void Request(string id, bool drag, bool light)
        {
            if (Busy || AnalysisWorkspace.Busy) return;
            var doc = RhinoDoc.ActiveDoc;
            if (doc == null || doc.InCommand(false) > 0)
            {
                RhinoApp.WriteLine("Finish the current Rhino command before placing a library model.");
                return;
            }
            Busy = true;
            Eto.Forms.Application.Instance.AsyncInvoke(() =>
            {
                try
                {
                    if (drag && !LeftDown) return;
                    PendingId = id; PendingDrag = drag; PendingLight = light;
                    RhinoApp.RunScript("_AlmondPlaceLibraryAsset", false);
                }
                catch (Exception ex) { RhinoApp.WriteLine("Almond placement: {0}", ex.Message); }
                finally { PendingId = null; Busy = false; }
            });
        }

        internal static Result Place(RhinoDoc doc, string id, bool drag, bool light)
        {
            string root = BridgeServer.ResolveLibraryDirectory("RHINO_MCP_DRAWING_ASSET_DIR", "DrawingAssetfiles");
            JObject asset = LibraryAssetSource.Read(root, id);
            if (doc.ModelUnitSystem == UnitSystem.None || doc.ModelUnitSystem == UnitSystem.CustomUnits)
                throw new InvalidDataException("Set standard document units before placing a model.");
            double scale = RhinoMath.UnitScale(UnitSystem.Millimeters, doc.ModelUnitSystem);
            var bounds = PreviewBounds(asset, scale);
            Point3d point;
            using (var get = new GetPoint())
            {
                get.SetCommandPrompt(drag ? "Release in a viewport to place; Esc cancels" : "Pick model insertion point; Esc cancels");
                get.EnableTransparentCommands(false);
                get.DynamicDraw += (s, e) =>
                {
                    if (!bounds.IsValid) return;
                    var box = new BoundingBox(bounds.Min + (Vector3d)e.CurrentPoint, bounds.Max + (Vector3d)e.CurrentPoint);
                    e.Display.DrawBox(box, Color.FromArgb(233, 68, 43), 2);
                };
                if (drag)
                {
                    if (!LeftDown) return Result.Cancel;
                    ReleaseCapture();
                    get.SetWaitDuration(150);
                }
                RhinoApp.SetFocusToMainWindow(doc);
                GetResult result;
                do { result = get.Get(drag); }
                while (drag && result == GetResult.Timeout && LeftDown);
                if (result != GetResult.Point || get.View() == null) return Result.Cancel;
                point = get.Point();
            }
            // The user may keep the point picker open while another process refreshes
            // this asset. Resolve the current record again for the actual placement.
            asset = LibraryAssetSource.Read(root, id);
            // The panel and MCP share registered-source verification and linked placement.
            // This native Rhino command owns its Undo record.
            var manager = new FurnitureAssetManager(root, "ALMOND-DRAW::ASSETS", "DRAWING",
                "drawing_asset", "model asset", new[] { ".3dm" });
            var metadata = (JObject)asset.DeepClone();
            metadata.Remove("_resolved_file");
            metadata["library_id"] = "model_assets";
            var placed = manager.PlaceInCommand(doc, new FurniturePlacementRequest {
                AssetId = id, FilePath = (string)asset["_resolved_file"], Name = (string)asset["product"] ?? id,
                Position = new[] { point.X, point.Y, point.Z }, RotationDegrees = 0, Scale = 1,
                Metadata = metadata
            });
            if (placed.Status != "success")
            {
                RhinoApp.WriteLine("Almond placement: {0}", placed.Message);
                if (placed.RequiresReconciliation) RhinoApp.WriteLine("Placement completion is uncertain. Inspect the document before retrying.");
                return Result.Failure;
            }
            doc.Objects.Select(Guid.Parse(placed.ObjectGuid));
            doc.Views.Redraw();
            RhinoApp.WriteLine("Placed {0} as a linked 3DM with document layers. Undo removes this placement.", asset["product"] ?? id);
            return Result.Success;
        }

        private static BoundingBox PreviewBounds(JObject asset, double unitScale)
        {
            // Dimensions alone cannot locate an arbitrary preserved source origin.
            if (!(asset["spatial"]?["bounds_mm"] is JArray values) || values.Count != 6) return BoundingBox.Empty;
            var numbers = new double[6];
            for (int i = 0; i < 6; i++)
            {
                if (values[i].Type != JTokenType.Integer && values[i].Type != JTokenType.Float) return BoundingBox.Empty;
                numbers[i] = (double)values[i] * unitScale;
                if (!Double.IsFinite(numbers[i])) return BoundingBox.Empty;
            }
            return new BoundingBox(numbers[0], numbers[1], numbers[2], numbers[3], numbers[4], numbers[5]);
        }
    }

    public sealed class AlmondPlaceLibraryAssetCommand : Command
    {
        public override string EnglishName => "AlmondPlaceLibraryAsset";
        protected override Result RunCommand(RhinoDoc doc, RunMode mode)
        {
            string id = LibraryPlacement.PendingId;
            if (id == null) { RhinoApp.WriteLine("Use Place or drag a model from AlmondLibrary."); return Result.Cancel; }
            LibraryPlacement.PendingId = null;
            try { return LibraryPlacement.Place(doc, id, LibraryPlacement.PendingDrag, LibraryPlacement.PendingLight); }
            catch (Exception ex) { RhinoApp.WriteLine("Almond placement: {0}", ex.Message); return Result.Failure; }
        }
    }
}
