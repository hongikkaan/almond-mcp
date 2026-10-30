using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Collections;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    // Fixed read-only queries. Object sets do not expand through groups or block definitions.
    public static class ObjectObservation
    {
        const int MaxBytes = 262144;
        static readonly Type SharedDictionaryType = typeof(Rhino.DocObjects.Custom.UserDictionary).Assembly
            .GetType("Rhino.DocObjects.Custom.SharedUserDictionary", throwOnError: true);
        // CommonObject.UserDictionary would attach a new dictionary even on a read.
        public static ArchivableDictionary ExistingDictionary(Rhino.Runtime.CommonObject owner) =>
            (owner.UserData.Find(SharedDictionaryType) as Rhino.DocObjects.Custom.UserDictionary)?.Dictionary;
        public static RhinoObject[] ModelObjects(RhinoDoc doc)
        {
            var objects = doc.Objects.GetObjectList(new ObjectEnumeratorSettings {
                NormalObjects = true, HiddenObjects = true, LockedObjects = true,
                ReferenceObjects = true, DeletedObjects = false, IdefObjects = false
            }).Where(o => o != null && !o.IsDeleted && !o.IsInstanceDefinitionGeometry &&
                o.Attributes.Space != ActiveSpace.PageSpace).Take(100001).ToArray();
            if (objects.Length > 100000) throw new ArgumentException("Document exceeds the 100000-object scan budget.");
            return objects;
        }

        public static RhinoObject[] VisibleObjects(RhinoDoc doc) => ModelObjects(doc).Where(o => o.Visible).ToArray();

        public static void ValidateDocument(RhinoDoc doc, JObject request)
        {
            if (doc == null) throw new ArgumentException("No Rhino document is available.");
            string expected = request.Value<string>("expected_model_path");
            if (String.IsNullOrWhiteSpace(expected) || !Path.IsPathRooted(expected) ||
                !String.Equals(expected, Path.GetFullPath(expected), StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("expected_model_path must be an absolute normalized path.");
            if (String.IsNullOrWhiteSpace(doc.Path) ||
                !String.Equals(Path.GetFullPath(doc.Path), expected, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("The active saved document differs from expected_model_path.");
            if (Encoding.UTF8.GetByteCount(request.ToString(Formatting.None)) > MaxBytes)
                throw new ArgumentException("Request exceeds 256 KiB.");
        }

        public static JObject Handle(RhinoDoc doc, JObject request)
        {
            try
            {
                ValidateDocument(doc, request);
                if ((string)request["type"] == "get_object_intersections")
                {
                    var ids = ReadIds(request["object_ids"], 512, true);
                    int maxPairs = Integer(request, "max_pairs", 64, 1, 64);
                    var result = ComponentOperations.CheckIntersectVolumes(doc, ids, maxPairs);
                    if ((string)result["status"] == "success")
                    {
                        result["schema"] = "almond-object-intersections/v1";
                        result["limitations"][0] = "All distinct pairs within the explicit object set are considered; groups do not expand it.";
                    }
                    return result;
                }
                if ((string)request["type"] != "get_rhino_objects") throw new ArgumentException("Unknown object observation request.");
                return Query(doc, request);
            }
            catch (InvalidOperationException ex) { return Error("document_mismatch", ex.Message); }
            catch (ArgumentException ex) { return Error("invalid_arguments", ex.Message); }
            catch (Exception ex) { return Error("object_observation_failed", ex.Message); }
        }

        public static Guid[] ReadIds(JToken value, int max, bool required)
        {
            if (value == null && !required) return Array.Empty<Guid>();
            var array = value as JArray;
            if (array == null || array.Count > max || (required && array.Count == 0) ||
                array.Any(t => t.Type != JTokenType.String || !Guid.TryParse((string)t, out var id) || id == Guid.Empty))
                throw new ArgumentException("object_ids must contain " + (required ? "1" : "0") + ".." + max + " nonempty GUIDs.");
            var ids = array.Values<string>().Select(Guid.Parse).ToArray();
            if (ids.Distinct().Count() != ids.Length) throw new ArgumentException("object_ids must be distinct.");
            return ids;
        }

        static int Integer(JObject request, string key, int fallback, int min, int max)
        {
            var token = request[key];
            if (token == null) return fallback;
            if (token.Type != JTokenType.Integer || (long)token < min || (long)token > max)
                throw new ArgumentException(key + " must be an integer in " + min + ".." + max + ".");
            return (int)token;
        }

        static JObject Query(RhinoDoc doc, JObject request)
        {
            string scope = (string)request["scope"] ?? "visible";
            var ids = ReadIds(request["object_ids"], 4096, scope == "ids");
            if (scope != "ids" && ids.Length != 0) throw new ArgumentException("object_ids requires scope=ids.");
            int offset = Integer(request, "offset", 0, 0, 100000), limit = Integer(request, "limit", 50, 1, 200);
            if (request["include_geometry"] != null && request["include_geometry"].Type != JTokenType.Boolean)
                throw new ArgumentException("include_geometry must be a boolean.");
            bool geometry = (bool?)request["include_geometry"] ?? false;
            var filters = request["filters"] as JObject ?? new JObject();
            if (request["filters"] != null && !(request["filters"] is JObject)) throw new ArgumentException("filters must be an object.");
            ValidateFilters(filters);
            var all = ModelObjects(doc);
            var visible = new HashSet<Guid>(all.Where(o => o.Visible).Select(o => o.Id));
            IEnumerable<RhinoObject> source;
            switch (scope)
            {
                case "visible": source = all.Where(o => visible.Contains(o.Id)); break;
                case "selected": source = all.Where(o => o.IsSelected(false) != 0); break;
                case "document": source = all; break;
                case "ids":
                    var byId = all.ToDictionary(o => o.Id);
                    var missing = ids.Where(id => !byId.ContainsKey(id)).ToArray();
                    if (missing.Length != 0) throw new ArgumentException("IDs are not top-level model objects: " + String.Join(",", missing));
                    source = ids.Select(id => byId[id]); break;
                default: throw new ArgumentException("scope must be visible, selected, ids or document.");
            }
            var candidates = source.ToArray();
            var matched = candidates.Where(o => Matches(doc, o, filters)).OrderBy(o => o.Id).ToArray();
            var set = new HashSet<Guid>(matched.Select(o => o.Id));
            var rows = new JArray();
            var budget = new ValueBudget();
            int rowBytes = 0;
            foreach (var obj in matched.Skip(offset).Take(limit))
            {
                var row = Describe(doc, obj, set, visible, geometry, budget);
                rowBytes += Encoding.UTF8.GetByteCount(row.ToString(Formatting.None));
                if (rowBytes > MaxBytes - 4096) return Error("observation_too_large", "Response exceeds 256 KiB; reduce limit, scope or geometry detail.");
                rows.Add(row);
            }
            var answer = new JObject {
                ["status"] = "success", ["schema"] = "almond-object-observation/v1",
                ["model_path"] = doc.Path, ["document_units"] = doc.ModelUnitSystem.ToString(),
                ["tolerance_model_units"] = doc.ModelAbsoluteTolerance, ["scope"] = scope,
                ["source_count"] = candidates.Length, ["matched_count"] = matched.Length,
                ["document_visible_count"] = visible.Count, ["matched_visible_count"] = matched.Count(o => visible.Contains(o.Id)),
                ["visible_outside_match_count"] = visible.Count(id => !set.Contains(id)),
                ["objects"] = rows, ["offset"] = offset, ["limit"] = limit,
                ["next_offset"] = offset + rows.Count < matched.Length ? new JValue(offset + rows.Count) : JValue.CreateNull(),
                ["complete"] = offset == 0 && rows.Count == matched.Length,
                ["visibility_basis"] = "Rhino document visibility, including object/layer hiding; not pixel, frustum, clipping or occlusion proof.",
                ["limitations"] = new JArray("Top-level model objects only; groups do not expand the set, block contents are not traversed.",
                    "Filters describe metadata, not architectural element identity. Scalar dictionary strings are not split into inferred lists.")
            };
            if (Encoding.UTF8.GetByteCount(answer.ToString(Formatting.None)) > MaxBytes)
                return Error("observation_too_large", "Response exceeds 256 KiB; reduce limit, scope or geometry detail.");
            return answer;
        }

        static void ValidateFilters(JObject filters)
        {
            if (filters.Properties().Any(p => p.Name != "layer_paths" && p.Name != "name_contains" && p.Name != "user_dictionary"))
                throw new ArgumentException("Filters support layer_paths, name_contains and user_dictionary only.");
            if (filters["layer_paths"] != null && (!(filters["layer_paths"] is JArray layers) || layers.Count == 0 || layers.Count > 64 ||
                layers.Any(v => v.Type != JTokenType.String || String.IsNullOrEmpty((string)v))))
                throw new ArgumentException("layer_paths must contain 1..64 exact full layer paths.");
            if (filters["name_contains"] != null && (filters["name_contains"].Type != JTokenType.String || ((string)filters["name_contains"]).Length > 256))
                throw new ArgumentException("name_contains must be a string of at most 256 characters.");
            if (filters["user_dictionary"] == null) return;
            if (!(filters["user_dictionary"] is JArray conditions) || conditions.Count > 16) throw new ArgumentException("user_dictionary must contain at most 16 conditions.");
            foreach (var item in conditions)
            {
                var c = item as JObject;
                if (c == null || c.Properties().Any(p => p.Name != "source" && p.Name != "key" && p.Name != "any_of") ||
                    ((string)c["source"] != "attributes" && (string)c["source"] != "geometry") ||
                    c["key"]?.Type != JTokenType.String || String.IsNullOrEmpty((string)c["key"]) ||
                    !(c["any_of"] is JArray values) || values.Count < 1 || values.Count > 64 || values.Any(v => !Scalar(v)))
                    throw new ArgumentException("Each dictionary condition requires source=attributes|geometry, key and 1..64 scalar any_of values.");
            }
        }

        static bool Scalar(JToken token) => token.Type == JTokenType.String || token.Type == JTokenType.Boolean ||
            token.Type == JTokenType.Integer || token.Type == JTokenType.Float;
        static bool Matches(RhinoDoc doc, RhinoObject obj, JObject filters)
        {
            if (filters["layer_paths"] is JArray layers && !layers.Values<string>().Contains(doc.Layers.FindIndex(obj.Attributes.LayerIndex)?.FullPath, StringComparer.OrdinalIgnoreCase)) return false;
            if (filters["name_contains"] != null && (obj.Name ?? "").IndexOf((string)filters["name_contains"], StringComparison.OrdinalIgnoreCase) < 0) return false;
            foreach (var c in filters["user_dictionary"] as JArray ?? new JArray())
            {
                var dictionary = ExistingDictionary((string)c["source"] == "attributes" ? (Rhino.Runtime.CommonObject)obj.Attributes : obj.Geometry);
                string key = (string)c["key"];
                if (dictionary == null || !dictionary.ContainsKey(key)) return false;
                var raw = dictionary[key];
                object[] values;
                if (!(raw is string) && raw is IEnumerable sequence && !(raw is ArchivableDictionary))
                {
                    values = sequence.Cast<object>().Take(4097).ToArray();
                    if (values.Length > 4096) throw new ArgumentException("Dictionary filter value exceeds 4096 items; narrow the object set.");
                }
                else values = new[] { raw };
                if (!values.Select(ScalarValue).Where(v => v != null).Any(v => ((JArray)c["any_of"]).Any(expected => JToken.DeepEquals(v, expected)))) return false;
            }
            return true;
        }

        sealed class ValueBudget { public int Nodes = 8192, Characters = 131072; }
        static JToken ScalarValue(object value)
        {
            if (value is string || value is bool || value is byte || value is short || value is int || value is long ||
                value is sbyte || value is ushort || value is uint || value is ulong || value is float || value is double || value is decimal)
                return JToken.FromObject(value);
            return null;
        }
        static JToken SafeValue(object value, int depth, ValueBudget budget)
        {
            if (--budget.Nodes < 0) return new JObject { ["value_omitted"] = true, ["reason"] = "metadata_budget" };
            if (value == null) return JValue.CreateNull();
            if (value is string text)
            {
                budget.Characters -= text.Length;
                if (budget.Characters < 0) return new JObject { ["value_omitted"] = true, ["reason"] = "metadata_budget" };
            }
            var scalar = ScalarValue(value);
            if (scalar != null) return scalar;
            if (value is Guid guid) return new JValue(guid.ToString());
            if (depth < 4 && value is ArchivableDictionary dictionary) return Dictionary(dictionary, budget, depth + 1);
            if (depth < 4 && value is IEnumerable sequence)
            {
                var items = sequence.Cast<object>().Take(257).ToArray();
                if (items.Length <= 256) return new JArray(items.Select(v => SafeValue(v, depth + 1, budget)));
            }
            return new JObject { ["unsupported_type"] = value.GetType().FullName, ["value_omitted"] = true };
        }
        static JObject Dictionary(ArchivableDictionary dictionary, ValueBudget budget, int depth = 0)
        {
            var data = new JObject();
            if (dictionary == null) return new JObject { ["values"] = data, ["total_keys"] = 0, ["truncated"] = false };
            foreach (string key in dictionary.Keys.Take(64))
            {
                budget.Characters -= key.Length;
                if (budget.Nodes <= 0 || budget.Characters < 0) break;
                data[key] = SafeValue(dictionary[key], depth, budget);
            }
            return new JObject { ["values"] = data, ["total_keys"] = dictionary.Count, ["truncated"] = dictionary.Count > data.Count };
        }
        static JArray Point(Point3d p) => new JArray(p.X, p.Y, p.Z);
        static JObject Bounds(BoundingBox b) => b.IsValid ? new JObject { ["min"] = Point(b.Min), ["max"] = Point(b.Max) } : null;
        static JObject Describe(RhinoDoc doc, RhinoObject obj, HashSet<Guid> matched, HashSet<Guid> visible, bool includeGeometry, ValueBudget budget)
        {
            var groups = new JArray();
            foreach (int index in (obj.Attributes.GetGroupList() ?? Array.Empty<int>()).Take(64))
            {
                var group = doc.Groups[index];
                var members = doc.Groups.GroupMembers(index) ?? Array.Empty<RhinoObject>();
                groups.Add(new JObject { ["id"] = group.Id.ToString(), ["name"] = group.Name,
                    ["member_count"] = members.Length, ["members_outside_match_count"] = members.Count(o => !matched.Contains(o.Id)),
                    ["visible_member_count"] = members.Count(o => visible.Contains(o.Id)),
                    ["member_ids"] = new JArray(members.Take(64).Select(o => o.Id.ToString())), ["members_truncated"] = members.Length > 64 });
            }
            var geometry = obj.Geometry;
            var row = new JObject { ["id"] = obj.Id.ToString(), ["name"] = obj.Name ?? "",
                ["layer_path"] = doc.Layers.FindIndex(obj.Attributes.LayerIndex)?.FullPath,
                ["object_type"] = obj.ObjectType.ToString(), ["geometry_kind"] = geometry.GetType().Name,
                ["geometry_crc"] = geometry.DataCRC(0), ["visible"] = visible.Contains(obj.Id),
                ["selected"] = obj.IsSelected(false) != 0, ["hidden"] = obj.IsHidden, ["locked"] = obj.IsLocked,
                ["bounds"] = Bounds(geometry.GetBoundingBox(true)), ["groups"] = groups,
                ["groups_truncated"] = obj.Attributes.GroupCount > 64,
                ["user_dictionary"] = new JObject { ["attributes"] = Dictionary(ExistingDictionary(obj.Attributes), budget), ["geometry"] = Dictionary(ExistingDictionary(geometry), budget) } };
            if (!includeGeometry) return row;
            row["geometry_valid"] = geometry.IsValid;
            if (geometry is Brep brep)
            {
                bool valid = geometry.IsValid, solid = brep.IsSolid, manifold = brep.IsManifold;
                row["solid"] = solid;
                row["manifold"] = manifold;
                row["face_count"] = brep.Faces.Count;
                row["faces_truncated"] = brep.Faces.Count > 128;
                var faces = new JArray();
                foreach (var face in brep.Faces.Take(128))
                {
                    bool planar = face.TryGetPlane(out var plane, doc.ModelAbsoluteTolerance);
                    var normal = face.OrientationIsReversed ? -plane.Normal : plane.Normal;
                    bool adjacentPlanar = planar && face.AdjacentEdges().SelectMany(i => brep.Edges[i].AdjacentFaces()).Distinct()
                        .All(i => brep.Faces[i].IsPlanar(doc.ModelAbsoluteTolerance));
                    faces.Add(new JObject { ["face_index"] = face.FaceIndex, ["planar"] = planar,
                        ["plane_origin"] = planar ? Point(plane.Origin) : null,
                        ["normal"] = planar ? new JArray(normal.X, normal.Y, normal.Z) : null,
                        ["bounds"] = Bounds(face.GetBoundingBox(true)),
                        ["face_edit_supported"] = valid && solid && manifold && adjacentPlanar && !obj.IsLocked && !obj.IsReference });
                }
                row["faces"] = faces;
                if (valid && solid)
                    using (var mass = VolumeMassProperties.Compute(brep)) row["volume"] = mass == null ? JValue.CreateNull() : new JValue(mass.Volume);
            }
            else row["face_edit_supported"] = false;
            return row;
        }
        static JObject Error(string code, string message) => new JObject { ["status"] = "error", ["error_code"] = code, ["message"] = message };
    }
}
