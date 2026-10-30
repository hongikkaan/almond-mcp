using System;
using System.Collections.Generic;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;

// Read-only observations of explicit document-level member pairs.
// This helper does not approve a connection or modify a Rhino document.
public static class SolidIntersections
{
    public static JObject AuditPairs(RhinoDoc doc, JObject q)
    {
        if (doc == null) throw new ArgumentNullException("doc");
        if (q == null) throw new ArgumentNullException("q");
        var pairs = q["pairs"] as JArray;
        if (pairs == null || pairs.Count == 0)
            throw new ArgumentException("pairs must be a nonempty array of [document GUID, document GUID].");
        double tolerance = q["tolerance"] == null ? doc.ModelAbsoluteTolerance : q["tolerance"].Value<double>();
        if (!Finite(tolerance) || tolerance <= 0) throw new ArgumentException("tolerance must be finite and positive, in document units.");
        int maxPairs = Limit(q, "max_pairs", 16, 1, 64);
        int maxBytes = Limit(q, "max_bytes", 48000, 4096, 262144);
        // Validate every requested handle before doing potentially expensive kernel work.
        var handles = new List<Guid[]>();
        foreach (JToken token in pairs)
        {
            var pair = token as JArray;
            Guid a, b;
            if (pair == null || pair.Count != 2 || !Guid.TryParse((string)pair[0], out a)
                || !Guid.TryParse((string)pair[1], out b) || a == Guid.Empty || b == Guid.Empty || a == b)
                throw new ArgumentException("Each pair must contain two distinct, nonempty document GUIDs.");
            handles.Add(new[] { a, b });
        }
        var rows = new JArray();
        var report = new JObject {
            ["schema"] = "almond-solid-intersections/v1",
            ["document_units"] = doc.ModelUnitSystem.ToString(),
            ["tolerance_model_units"] = tolerance,
            ["requested_pairs"] = handles.Count,
            ["evaluated_pairs"] = 0,
            ["pairs"] = rows,
            ["truncated"] = false,
            ["truncation_reason"] = JValue.CreateNull(),
            ["limitations"] = new JArray(
                "Geometry observations only; no structural, fabrication, or waterproofing approval.",
                "Only explicit document-level Breps and Extrusions are supported; block members require resolved world-space geometry.",
                "bbox_distance_lower_bound is a lower bound, not the measured surface gap.",
                "Unknown intersection results are not zero.")
        };
        int count = Math.Min(handles.Count, maxPairs);
        for (int i = 0; i < count; i++)
        {
            JObject row = AuditPair(doc, handles[i][0], handles[i][1], tolerance);
            row["pair_index"] = i;
            rows.Add(row);
            report["evaluated_pairs"] = rows.Count;
            // Reserve room for truncation metadata; never emit a partial pair record.
            if (Encoding.UTF8.GetByteCount(report.ToString(Formatting.None)) > maxBytes - 256)
            {
                rows.RemoveAt(rows.Count - 1);
                report["evaluated_pairs"] = rows.Count;
                report["truncated"] = true;
                report["truncation_reason"] = "max_bytes";
                break;
            }
        }
        if (rows.Count < handles.Count && !(bool)report["truncated"])
        {
            report["truncated"] = true;
            report["truncation_reason"] = "max_pairs";
        }
        return report;
    }

    private static JObject AuditPair(RhinoDoc doc, Guid aId, Guid bId, double tolerance)
    {
        Brep a = null, b = null;
        var row = new JObject { ["a_id"] = aId.ToString(), ["b_id"] = bId.ToString() };
        try
        {
            JObject aInfo, bInfo;
            a = Member(doc, aId, out aInfo);
            b = Member(doc, bId, out bInfo);
            row["a"] = aInfo;
            row["b"] = bInfo;
            if (a == null || b == null)
            {
                row["status"] = "unsupported_input";
                row["overlap"] = Unknown("One or both inputs are unavailable, unsupported, invalid, open, or have unresolved orientation.");
                return row;
            }
            BoundingBox aBox = a.GetBoundingBox(true), bBox = b.GetBoundingBox(true);
            if (!aBox.IsValid || !bBox.IsValid)
            {
                row["status"] = "unknown";
                row["overlap"] = Unknown("Invalid bounding box.");
                return row;
            }
            double lowerBound = BoxDistance(aBox, bBox);
            row["bbox_distance_lower_bound"] = lowerBound;
            row["bbox_distance_units"] = doc.ModelUnitSystem.ToString();
            row["surface_gap"] = JValue.CreateNull();
            row["surface_gap_status"] = "not_measured";
            row["overlap"] = lowerBound > tolerance
                ? new JObject { ["status"] = "zero_volume", ["volume_model_units3"] = 0.0,
                    ["method"] = "disjoint_bounding_boxes", ["boolean_intersection_performed"] = false }
                : Intersect(a, b, tolerance);
            row["status"] = "observed";
            return row;
        }
        catch (Exception ex)
        {
            row["status"] = "unknown";
            row["error"] = Short(ex.GetType().Name + ": " + ex.Message, 320);
            if (row["overlap"] == null) row["overlap"] = Unknown("Intersection observation failed before an intersection observation was available.");
            return row;
        }
        finally
        {
            if (a != null) a.Dispose();
            if (b != null) b.Dispose();
        }
    }

    private static Brep Member(RhinoDoc doc, Guid id, out JObject info)
    {
        info = new JObject { ["id"] = id.ToString(), ["supported"] = false };
        RhinoObject obj = doc.Objects.FindId(id);
        if (obj == null || obj.IsDeleted) { info["reason"] = "not_found"; return null; }
        info["object_type"] = obj.ObjectType.ToString();
        info["name"] = Short(obj.Attributes.Name ?? "", 128);
        if (obj.IsInstanceDefinitionGeometry)
        {
            info["reason"] = "definition_member_requires_world_space_resolution";
            return null;
        }
        GeometryBase geometry = obj.Geometry;
        if (!(geometry is Brep) && !(geometry is Extrusion))
        {
            info["reason"] = "only_document_level_brep_or_extrusion_supported";
            return null;
        }
        info["source_is_valid"] = geometry.IsValid;
        Brep copy = geometry is Brep ? ((Brep)geometry).DuplicateBrep() : ((Extrusion)geometry).ToBrep();
        if (copy == null) { info["reason"] = "brep_conversion_failed"; return null; }
        info["is_valid"] = copy.IsValid;
        info["is_solid"] = copy.IsSolid;
        info["solid_orientation"] = copy.SolidOrientation.ToString();
        info["face_count"] = copy.Faces.Count;
        info["flipped_copy"] = false;
        if (!geometry.IsValid || !copy.IsValid || !copy.IsSolid)
        {
            info["reason"] = "valid_closed_solid_required";
            copy.Dispose();
            return null;
        }
        if (copy.SolidOrientation == BrepSolidOrientation.Inward)
        {
            copy.Flip();
            info["flipped_copy"] = true;
        }
        if (copy.SolidOrientation != BrepSolidOrientation.Outward)
        {
            info["reason"] = "unresolved_solid_orientation";
            copy.Dispose();
            return null;
        }
        info["supported"] = true;
        return copy;
    }

    private static JObject Intersect(Brep a, Brep b, double tolerance)
    {
        Brep ac = null, bc = null;
        Brep[] result = null;
        try
        {
            ac = a.DuplicateBrep(); bc = b.DuplicateBrep();
            result = Brep.CreateBooleanIntersection(ac, bc, tolerance);
            if (result == null) return Unknown("BooleanIntersection returned null.");
            if (result.Length == 0)
                return UnionVolumeBalance(a, b, tolerance);
            double volume = 0.0;
            foreach (Brep part in result)
            {
                if (part == null || !part.IsValid || !part.IsSolid)
                    return Unknown("BooleanIntersection returned a null, invalid, or nonclosed piece.", result.Length);
                using (VolumeMassProperties mass = VolumeMassProperties.Compute(part))
                {
                    if (mass == null || !Finite(mass.Volume))
                        return Unknown("Intersection volume computation failed.", result.Length);
                    volume += Math.Abs(mass.Volume);
                    if (!Finite(volume)) return Unknown("Intersection volume is not finite.", result.Length);
                }
            }
            return new JObject {
                ["status"] = volume > 0.0 ? "positive_volume" : "zero_volume",
                ["volume_model_units3"] = volume,
                ["method"] = "boolean_intersection",
                ["boolean_intersection_performed"] = true,
                ["result_count"] = result.Length
            };
        }
        catch (Exception ex) { return Unknown(Short(ex.GetType().Name + ": " + ex.Message, 320)); }
        finally
        {
            Dispose(result);
            if (ac != null) ac.Dispose();
            if (bc != null) bc.Dispose();
        }
    }

    // Rhino 8 can omit wholly contained solids from an empty intersection result.
    // The exact CSG volume identity provides a separate kernel-based observation;
    // never infer containment from point samples, nor infer zero from an empty result.
    private static JObject UnionVolumeBalance(Brep a, Brep b, double tolerance)
    {
        const double machineEpsilon = 2.2204460492503131e-16;
        Brep ac = null, bc = null;
        Brep[] union = null;
        try
        {
            double aVolume, aError, bVolume, bError;
            MeasureSolid(a, out aVolume, out aError);
            MeasureSolid(b, out bVolume, out bError);
            ac = a.DuplicateBrep(); bc = b.DuplicateBrep();
            union = Brep.CreateBooleanUnion(new[] { ac, bc }, tolerance);
            if (union == null || union.Length == 0)
                return Unknown("Empty BooleanIntersection; BooleanUnion volume balance is unavailable.", 0);
            double unionVolume = 0.0, unionError = 0.0;
            foreach (Brep part in union)
            {
                double partVolume, partError;
                MeasureSolid(part, out partVolume, out partError);
                unionVolume += partVolume;
                unionError += partError + 2 * machineEpsilon * (Math.Abs(unionVolume) + Math.Abs(partVolume));
                if (!Finite(unionVolume) || !Finite(unionError))
                    return Unknown("Empty BooleanIntersection; union volume or uncertainty is not finite.", 0);
            }
            double overlap = aVolume + bVolume - unionVolume;
            double uncertainty = aError + bError + unionError
                + 8 * machineEpsilon * (Math.Abs(aVolume) + Math.Abs(bVolume) + Math.Abs(unionVolume));
            if (!Finite(overlap) || !Finite(uncertainty) || uncertainty < 0)
                return Unknown("Empty BooleanIntersection; volume balance or uncertainty is not finite.", 0);
            if (overlap <= uncertainty)
                return Unknown("Empty BooleanIntersection; union volume balance does not establish positive overlap above numeric uncertainty. No zero-volume inference was made.", 0);
            if (overlap > Math.Min(aVolume, bVolume) + uncertainty)
                return Unknown("Empty BooleanIntersection; union volume balance exceeds the smaller operand volume.", 0);
            return new JObject {
                ["status"] = "positive_volume",
                ["volume_model_units3"] = overlap,
                ["method"] = "boolean_union_volume_balance",
                ["boolean_intersection_performed"] = true,
                ["result_count"] = 0,
                ["union_result_count"] = union.Length,
                ["operands_model_units3"] = new JObject {
                    ["a_volume"] = aVolume, ["b_volume"] = bVolume, ["union_volume"] = unionVolume },
                ["numeric_uncertainty_model_units3"] = uncertainty
            };
        }
        catch (Exception ex)
        {
            return Unknown("Empty BooleanIntersection; union volume balance failed: " + Short(ex.GetType().Name + ": " + ex.Message, 260), 0);
        }
        finally
        {
            Dispose(union);
            if (ac != null) ac.Dispose();
            if (bc != null) bc.Dispose();
        }
    }

    private static void MeasureSolid(Brep value, out double volume, out double error)
    {
        volume = 0.0; error = 0.0;
        if (value == null || !value.IsValid || !value.IsSolid || value.SolidOrientation != BrepSolidOrientation.Outward)
            throw new InvalidOperationException("Volume balance requires valid closed outward solids.");
        using (VolumeMassProperties mass = VolumeMassProperties.Compute(value))
        {
            if (mass == null || !Finite(mass.Volume) || mass.Volume <= 0 || !Finite(mass.VolumeError) || mass.VolumeError < 0)
                throw new InvalidOperationException("A finite positive solid volume and nonnegative volume uncertainty are required.");
            volume = mass.Volume;
            error = mass.VolumeError;
        }
    }

    private static JObject Unknown(string reason, int? count = null)
    {
        var value = new JObject { ["status"] = "unknown", ["volume_model_units3"] = JValue.CreateNull(), ["reason"] = reason };
        if (count.HasValue) value["result_count"] = count.Value;
        return value;
    }
    private static double BoxDistance(BoundingBox a, BoundingBox b)
    {
        double x = Math.Max(0, Math.Max(a.Min.X - b.Max.X, b.Min.X - a.Max.X));
        double y = Math.Max(0, Math.Max(a.Min.Y - b.Max.Y, b.Min.Y - a.Max.Y));
        double z = Math.Max(0, Math.Max(a.Min.Z - b.Max.Z, b.Min.Z - a.Max.Z));
        return Math.Sqrt(x * x + y * y + z * z);
    }
    private static int Limit(JObject q, string name, int fallback, int min, int max)
    {
        int value = q[name] == null ? fallback : q[name].Value<int>();
        if (value < min || value > max) throw new ArgumentException(name + " must be between " + min + " and " + max + ".");
        return value;
    }
    private static bool Finite(double value) { return !double.IsNaN(value) && !double.IsInfinity(value); }
    private static string Short(string value, int max) { return value.Length <= max ? value : value.Substring(0, max); }
    private static void Dispose(Brep[] values)
    {
        if (values == null) return;
        foreach (Brep value in values) if (value != null) value.Dispose();
    }
}
