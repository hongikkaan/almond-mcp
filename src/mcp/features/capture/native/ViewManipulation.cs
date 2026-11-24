using System;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Display;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    // An atomic, relative operation on one active model perspective, not a scene edit.
    internal static class ViewManipulation
    {
        private const double Epsilon = 1e-8;
        internal record Pose(Point3d Location, Point3d Target, Vector3d Direction, Vector3d Up);

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            RhinoViewport viewport = null;
            RhinoView view = null;
            ViewportInfo original = null;
            Pose before = null;
            double[] frustum = null;
            bool dispatched = false;
            string code = "invalid_arguments";
            try
            {
                ObjectObservation.ValidateDocument(doc, request);
                code = "unsupported_viewport";
                view = doc.Views.ActiveView;
                if (doc.IsHeadless || view == null || view is RhinoPageView)
                    throw new ArgumentException("Use an active normal perspective model viewport.");
                viewport = view.ActiveViewport;
                ValidateActive(doc, view, viewport);
                code = "invalid_arguments";
                var expected = request["expected_viewport_id"];
                if (expected != null)
                {
                    if (expected.Type != JTokenType.String || !Guid.TryParse((string)expected, out var id) || id == Guid.Empty)
                        throw new ArgumentException("Invalid expected_viewport_id.");
                    if (viewport.Id != id)
                    {
                        code = "viewport_mismatch";
                        throw new InvalidOperationException("The active viewport is not the expected viewport.");
                    }
                }

                original = new ViewportInfo(viewport);
                before = Read(viewport);
                frustum = Frustum(viewport);
                var proposed = new ViewportInfo(viewport);
                var after = before;
                var desiredFrustum = frustum;
                switch ((string)request["operation"])
                {
                    case "rotate":
                        if (request.ContainsKey("factor")) throw new ArgumentException("factor is zoom-only.");
                        string mode = (string)request["mode"];
                        if (mode != "look" && mode != "orbit") throw new ArgumentException("Use look or orbit.");
                        after = Rotate(before, mode == "orbit", Number(request, "yaw_deg", 0), Number(request, "pitch_deg", 0));
                        if (!proposed.SetCameraLocation(after.Location) || !proposed.SetCameraDirection(after.Direction)
                            || !proposed.SetCameraUp(after.Up))
                            throw new InvalidOperationException("The rotated camera frame is invalid.");
                        break;
                    case "zoom":
                        if (new[] { "mode", "yaw_deg", "pitch_deg" }.Any(request.ContainsKey))
                            throw new ArgumentException("mode and angles are rotate-only.");
                        desiredFrustum = Zoom(frustum, Number(request, "factor"));
                        if (!proposed.SetFrustum(desiredFrustum[0], desiredFrustum[1], desiredFrustum[2],
                            desiredFrustum[3], desiredFrustum[4], desiredFrustum[5]))
                            throw new ArgumentException("The requested zoom is outside the supported frustum.");
                        break;
                    default: throw new ArgumentException("Use rotate or zoom.");
                }

                ValidateActive(doc, view, viewport);
                if (Matches(before, after, frustum, desiredFrustum))
                    return Success(viewport, before, false);

                code = "view_manipulation_failed";
                dispatched = true;
                if (!viewport.SetViewProjection(proposed, false))
                    throw new InvalidOperationException("Rhino rejected the viewport projection.");
                if (after.Target != before.Target) viewport.SetCameraTarget(after.Target, false);
                view.Redraw();
                ValidateActive(doc, view, viewport);
                var actual = Read(viewport);
                if (!Matches(actual, after, Frustum(viewport), desiredFrustum))
                    throw new InvalidOperationException("Rhino did not apply the requested viewport transform.");
                return Success(viewport, actual, true);
            }
            catch (Exception exception)
            {
                bool unknown = false;
                if (dispatched)
                {
                    // Roll back only while this is still the same active viewport/document.
                    try
                    {
                        ValidateActive(doc, view, viewport);
                        if (!viewport.SetViewProjection(original, false))
                            throw new InvalidOperationException("Rhino rejected viewport restoration.");
                        viewport.SetCameraTarget(before.Target, false);
                        view.Redraw();
                        ValidateActive(doc, view, viewport);
                        unknown = !Matches(Read(viewport), before, Frustum(viewport), frustum);
                    }
                    catch { unknown = true; }
                }
                return new JObject { ["status"] = "error", ["error_code"] = code, ["message"] = exception.Message,
                    ["mutation_applied"] = unknown ? JValue.CreateNull() : new JValue(false),
                    ["requires_reconciliation"] = unknown };
            }
        }

        private static void ValidateActive(RhinoDoc doc, RhinoView view, RhinoViewport viewport)
        {
            if (RhinoDoc.ActiveDoc?.RuntimeSerialNumber != doc.RuntimeSerialNumber ||
                viewport == null || view is RhinoPageView || viewport.Id == Guid.Empty ||
                doc.Views.ActiveView?.ActiveViewport.Id != viewport.Id ||
                !viewport.IsPerspectiveProjection || viewport.IsTwoPointPerspectiveProjection)
                throw new InvalidOperationException("The active normal perspective model viewport changed or is unavailable.");
            if (Rhino.Commands.Command.InCommand() || doc.UndoRecordingIsActive || doc.UndoActive || doc.RedoActive)
                throw new InvalidOperationException("Complete the current command or Undo/Redo first.");
        }

        private static double Number(JObject request, string key, double? defaultValue = null)
        {
            var token = request[key];
            if (token == null && defaultValue.HasValue) return defaultValue.Value;
            if (token == null || (token.Type != JTokenType.Integer && token.Type != JTokenType.Float))
                throw new ArgumentException($"{key} must be a finite number.");
            double number = token.Value<double>();
            if (!double.IsFinite(number)) throw new ArgumentException($"{key} must be a finite number.");
            return number;
        }

        private static Pose Read(RhinoViewport viewport)
        {
            var pose = new Pose(viewport.CameraLocation, viewport.CameraTarget, viewport.CameraDirection, viewport.CameraUp);
            if (!pose.Location.IsValid || !pose.Target.IsValid || !pose.Direction.IsValid || !pose.Up.IsValid)
                throw new InvalidOperationException("The viewport does not have a valid camera frame and target.");
            return pose;
        }

        private static double[] Frustum(RhinoViewport viewport)
        {
            if (!viewport.GetFrustum(out double left, out double right, out double bottom, out double top,
                out double near, out double far) || near <= 0)
                throw new InvalidOperationException("No valid perspective frustum is available.");
            return new[] { left, right, bottom, top, near, far };
        }

        internal static Pose Rotate(Pose pose, bool orbit, double yaw, double pitch)
        {
            if (yaw == 0 && pitch == 0) throw new ArgumentException("Specify a nonzero rotation.");
            var direction = Unit(pose.Direction);
            var right = Unit(Vector3d.CrossProduct(direction, pose.Up));
            var up = Vector3d.CrossProduct(right, direction);
            var offset = orbit ? pose.Location - pose.Target : pose.Target - pose.Location;
            RotateAround(up, yaw, orbit ? 1 : -1, ref right, ref direction, ref offset);
            RotateAround(right, pitch, orbit ? -1 : 1, ref up, ref direction, ref offset);
            if (Math.Sqrt(direction.X * direction.X + direction.Y * direction.Y) <= Epsilon)
                throw new ArgumentException("A vertical camera direction is not supported.");
            var location = orbit ? pose.Target + offset : pose.Location;
            var target = orbit ? pose.Target : pose.Location + offset;
            if (!location.IsValid || !target.IsValid) throw new ArgumentException("Invalid rotated camera coordinates.");
            return new Pose(location, target, direction, up);
        }

        private static void RotateAround(Vector3d axis, double angle, int sign,
            ref Vector3d first, ref Vector3d second, ref Vector3d third)
        {
            double radians = Math.IEEERemainder(angle, 360) * sign * Math.PI / 180;
            double cosine = Math.Cos(radians), sine = Math.Sin(radians);
            Vector3d Rotated(Vector3d vector) => vector * cosine + Vector3d.CrossProduct(axis, vector) * sine
                + axis * ((axis.X * vector.X + axis.Y * vector.Y + axis.Z * vector.Z) * (1 - cosine));
            first = Rotated(first);
            second = Rotated(second);
            third = Rotated(third);
        }

        private static Vector3d Unit(Vector3d vector)
        {
            double length = Math.Sqrt(vector.X * vector.X + vector.Y * vector.Y + vector.Z * vector.Z);
            if (!double.IsFinite(length) || length <= Epsilon) throw new ArgumentException("Invalid camera basis.");
            return vector * (1 / length);
        }

        internal static double[] Zoom(double[] frustum, double factor)
        {
            if (!double.IsFinite(factor) || factor <= 0) throw new ArgumentException("factor must be finite and positive.");
            var zoomed = (double[])frustum.Clone();
            foreach (int min in new[] { 0, 2 })
            {
                double center = frustum[min] * 0.5 + frustum[min + 1] * 0.5;
                double half = (frustum[min + 1] * 0.5 - frustum[min] * 0.5) / factor;
                zoomed[min] = center - half;
                zoomed[min + 1] = center + half;
                if (!double.IsFinite(zoomed[min]) || !double.IsFinite(zoomed[min + 1]) || zoomed[min] >= zoomed[min + 1])
                    throw new ArgumentException("Zoom would collapse or overflow the perspective frustum.");
            }
            return zoomed;
        }

        private static bool Matches(Pose actual, Pose expected, double[] actualFrustum, double[] expectedFrustum) =>
            actual.Location.DistanceTo(expected.Location) <= Epsilon * Math.Max(1, (expected.Target - expected.Location).Length) &&
            actual.Target.DistanceTo(expected.Target) <= Epsilon * Math.Max(1, (expected.Target - expected.Location).Length) &&
            (actual.Direction - expected.Direction).Length <= Epsilon && (actual.Up - expected.Up).Length <= Epsilon &&
            Math.Abs(actualFrustum[4] - expectedFrustum[4]) <= Epsilon * expectedFrustum[4] &&
            Math.Abs(actualFrustum[5] - expectedFrustum[5]) <= Epsilon * expectedFrustum[5] &&
            Enumerable.Range(0, 4).All(i => Math.Abs(actualFrustum[i] - expectedFrustum[i]) <=
                Epsilon * Math.Max(expectedFrustum[4], Math.Abs(expectedFrustum[i])));

        private static JObject Success(RhinoViewport viewport, Pose pose, bool applied) =>
            new JObject { ["status"] = "success", ["viewport_id"] = viewport.Id.ToString(),
                ["camera_location"] = new JArray(pose.Location.X, pose.Location.Y, pose.Location.Z),
                ["camera_target"] = new JArray(pose.Target.X, pose.Target.Y, pose.Target.Z),
                ["mutation_applied"] = applied, ["requires_reconciliation"] = false };
    }
}
