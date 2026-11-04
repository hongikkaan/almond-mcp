using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.Collections;
using Rhino.DocObjects;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    // Fixed read-only queries. Hierarchy expansion never adds unrelated document objects.
    public static partial class ObjectObservation
    {
        const int MaxBytes = 262144;
        static readonly HashSet<string> ObjectFields = new HashSet<string>(new[] {
            "id", "name", "layer_path", "object_type", "geometry_kind", "geometry_crc",
            "visible", "selected", "hidden", "locked", "bounds", "groups", "user_dictionary",
            "geometry_valid", "solid", "manifold", "volume", "faces", "face_count"
        }, StringComparer.Ordinal);
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
                    if (request["include_blocks"] != null && request["include_blocks"].Type != JTokenType.Boolean)
                        throw new ArgumentException("include_blocks must be boolean.");
                    if (request["cursor"] != null && (request["cursor"].Type != JTokenType.String || ((string)request["cursor"]).Length > 256))
                        throw new ArgumentException("cursor must be a string of at most 256 characters.");
                    bool includeBlocks = (bool?)request["include_blocks"] ?? false;
                    string cursor = (string)request["cursor"] ?? "";
                    if (request["stop_at_first_positive"] != null && request["stop_at_first_positive"].Type != JTokenType.Boolean)
                        throw new ArgumentException("stop_at_first_positive must be boolean.");
                    bool stop = (bool?)request["stop_at_first_positive"] ?? false;
                    var result = stop ? IntersectionAnalysis.QueryForPreview(doc, ids, maxPairs, includeBlocks, cursor, null, true)
                        : ComponentOperations.CheckIntersectVolumes(doc, ids, maxPairs, includeBlocks, cursor);
                    if ((string)result["status"] == "success")
                    {
                        result["schema"] = "almond-object-intersections/v1";
                        result["limitations"][0] = "All distinct pairs within the explicit object set are considered; groups do not expand it. include_blocks controls block occurrence traversal.";
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
            bool current = scope == "current";
            bool selected = Boolean(request, "selected"), insideWindow = Boolean(request, "inside_window");
            bool recursive = Boolean(request, "recursive");
            if (selected && insideWindow) throw new ArgumentException("Choose selected or inside_window, not both.");
            if (!current && (selected || insideWindow)) throw new ArgumentException("selected and inside_window require scope=current.");
            var ids = ReadIds(request["object_ids"], 4096, scope == "ids");
            bool idScope = scope == "ids" || (scope == "document" && ids.Length != 0);
            if (!idScope && ids.Length != 0) throw new ArgumentException("object_ids requires scope=document.");
            Guid[] groupIds;
            try { groupIds = ReadIds(request["group_ids"], 64, scope == "groups"); }
            catch (ArgumentException ex) { throw new ArgumentException(ex.Message.Replace("object_ids", "group_ids")); }
            if (groupIds.Length != 0 && (ids.Length != 0 || !new[] { "current", "document", "groups" }.Contains(scope)))
                throw new ArgumentException("group_ids requires current/document scope without object_ids.");
            int offset = Integer(request, "offset", 0, 0, 100000), limit = Integer(request, "limit", 50, 1, 200);
            if (request["include_geometry"] != null && request["include_geometry"].Type != JTokenType.Boolean)
                throw new ArgumentException("include_geometry must be a boolean.");
            bool geometry = (bool?)request["include_geometry"] ?? false;
            string mode = (string)request["result_mode"] ?? "objects";
            if (mode != "objects" && mode != "hierarchy" && mode != "summary")
                throw new ArgumentException("result_mode must be objects, hierarchy or summary.");
            bool expandGroups = recursive || Boolean(request, "expand_groups"), expandBlocks = recursive || Boolean(request, "expand_blocks");
            if (recursive && mode == "objects") mode = "hierarchy";
            int depth = Integer(request, "depth", 1, 1, 8);
            if (mode != "hierarchy" && (expandGroups || expandBlocks || depth != 1))
                throw new ArgumentException("Expansion and depth require result_mode=hierarchy.");
            HashSet<string> fields = null;
            if (request["fields"] != null && request["fields"].Type != JTokenType.Null)
            {
                if (!(request["fields"] is JArray names) || names.Count == 0 ||
                    names.Any(v => v.Type != JTokenType.String || !ObjectFields.Contains((string)v)))
                    throw new ArgumentException("fields contains an unsupported object field.");
                fields = new HashSet<string>(names.Values<string>(), StringComparer.Ordinal);
                if (fields.Count != names.Count) throw new ArgumentException("fields must be distinct.");
            }
            int faceOffset = Integer(request, "face_offset", 0, 0, 100000);
            int faceLimit = Integer(request, "face_limit", 128, 1, 128);
            bool wantsFaces = fields == null ? geometry : fields.Contains("faces");
            if ((faceOffset != 0 || faceLimit != 128) && !wantsFaces)
                throw new ArgumentException("Face pagination requires include_geometry=true or fields containing faces.");
            var expected = new Dictionary<Guid, uint>();
            if (request["expected_geometry_crcs"] != null)
            {
                if (!(request["expected_geometry_crcs"] is JObject crcs) || crcs.Count > 4096)
                    throw new ArgumentException("expected_geometry_crcs must map at most 4096 object GUIDs to uint32 CRCs.");
                foreach (var entry in crcs.Properties())
                {
                    if (!Guid.TryParse(entry.Name, out var id) || id == Guid.Empty || expected.ContainsKey(id) ||
                        entry.Value.Type != JTokenType.Integer || (long)entry.Value < 0 || (long)entry.Value > UInt32.MaxValue)
                        throw new ArgumentException("expected_geometry_crcs requires distinct object GUIDs and uint32 CRCs.");
                    expected.Add(id, (uint)entry.Value);
                }
            }
            if (expected.Count != 0 && (!idScope || expected.Keys.Any(id => !ids.Contains(id))))
                throw new ArgumentException("expected_geometry_crcs keys must belong to the explicit object_ids set.");
            if (faceOffset != 0 && (!idScope || expected.Count != ids.Length))
                throw new ArgumentException("A subsequent face page requires document object_ids and an observed CRC for every object.");
            if (mode == "summary" && (fields != null || geometry || expected.Count != 0 || faceOffset != 0 || faceLimit != 128))
                throw new ArgumentException("Summary returns layer/type counts; object fields and face options require result_mode=objects.");
            if (mode == "hierarchy" && (geometry || expected.Count != 0 || faceOffset != 0 || faceLimit != 128 ||
                (fields != null && fields.Overlaps(new[] { "geometry_valid", "solid", "manifold", "volume", "faces", "face_count" }))))
                throw new ArgumentException("Geometry detail and face editing references require result_mode=objects.");
            var filters = request["filters"] as JObject ?? new JObject();
            if (request["filters"] != null && !(request["filters"] is JObject)) throw new ArgumentException("filters must be an object.");
            ValidateFilters(filters);
            var all = ModelObjects(doc);
            var visible = new HashSet<Guid>(all.Where(o => o.Visible).Select(o => o.Id));
            var editing = EditingContext.ObserveObjects(doc);
            var editor = editing.State;
            var viewport = insideWindow ? doc.Views.ActiveView?.ActiveViewport : null;
            if (insideWindow && (viewport == null || doc.ActiveSpace != ActiveSpace.ModelSpace))
                return Error("model_viewport_required", "inside_window requires an active model viewport or model Detail.");
            IEnumerable<RhinoObject> source;
            switch (scope)
            {
                case "visible": source = all.Where(o => visible.Contains(o.Id)); break;
                case "selected": source = all.Where(o => o.IsSelected(false) != 0); break;
                case "current":
                    source = CurrentObjects(doc, all, selected, insideWindow);
                    break;
                case "document":
                    if (!idScope) { source = all; break; }
                    goto case "ids";
                case "ids":
                    var byId = all.ToDictionary(o => o.Id);
                    var missing = ids.Where(id => !byId.ContainsKey(id)).ToArray();
                    if (missing.Length != 0) throw new ArgumentException("IDs are not top-level model objects: " + String.Join(",", missing));
                    source = ids.Select(id => byId[id]); break;
                case "groups":
                    var modelIds = new HashSet<Guid>(all.Select(o => o.Id));
                    source = RequestedGroups(doc, groupIds, editing).SelectMany(g => g.Members)
                        .Where(o => modelIds.Contains(o.Id)).GroupBy(o => o.Id).Select(g => g.First()); break;
                default: throw new ArgumentException("scope must be current or document.");
            }
            if (groupIds.Length != 0 && scope != "groups")
            {
                var groupMembers = new HashSet<Guid>(RequestedGroups(doc, groupIds, editing).SelectMany(g => g.Members).Select(o => o.Id));
                source = source.Where(o => groupMembers.Contains(o.Id));
            }
            var candidates = source.ToArray();
            var matched = candidates.Where(o => Matches(doc, o, filters)).OrderBy(o => o.Id).ToArray();
            foreach (var obj in candidates)
                if (expected.TryGetValue(obj.Id, out var crc) && obj.Geometry.DataCRC(0) != crc)
                    return Error("stale_geometry", "An object's geometry changed; observe its faces from the beginning: " + obj.Id);
            var set = new HashSet<Guid>(matched.Select(o => o.Id));
            string snapshot = SnapshotToken(doc, request, all, editor);
            string wantedSnapshot = (string)request["expected_snapshot"] ?? "";
            if (wantedSnapshot.Length != 0 && !String.Equals(wantedSnapshot, snapshot, StringComparison.Ordinal))
                return Error("observation_changed", "The model, editor, selection, view or query changed; restart at offset=0.");
            if (request["recursive"] != null && offset > 0 && wantedSnapshot.Length == 0)
                throw new ArgumentException("Subsequent pages require expected_snapshot from the first page.");
            if (mode == "hierarchy")
            {
                var hierarchy = Hierarchy(doc, scope, groupIds, candidates, matched, visible,
                    fields, expandGroups, expandBlocks, depth, offset, limit, editing);
                return QueryEvidence(hierarchy, editor, snapshot, current, selected, insideWindow);
            }
            var rows = new JArray();
            var budget = new ValueBudget();
            int rowBytes = 0;
            int rowCount = matched.Length;
            IEnumerable<JObject> page;
            if (mode == "summary")
            {
                var groups = matched.GroupBy(o => new {
                    Layer = doc.Layers.FindIndex(o.Attributes.LayerIndex)?.FullPath,
                    Type = o.ObjectType.ToString(), Kind = o.Geometry.GetType().Name
                }).OrderBy(g => g.Key.Layer, StringComparer.Ordinal).ThenBy(g => g.Key.Type, StringComparer.Ordinal)
                    .ThenBy(g => g.Key.Kind, StringComparer.Ordinal).ToArray();
                rowCount = groups.Length;
                page = groups.Skip(offset).Take(limit).Select(g => new JObject {
                    ["layer_path"] = g.Key.Layer, ["object_type"] = g.Key.Type, ["geometry_kind"] = g.Key.Kind,
                    ["object_count"] = g.Count(), ["visible_count"] = g.Count(o => visible.Contains(o.Id))
                });
            }
            else page = matched.Skip(offset).Take(limit).Select(obj =>
                Describe(doc, obj, set, visible, geometry, budget, fields, faceOffset, faceLimit, editing));
            foreach (var row in page)
            {
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
                [mode == "summary" ? "summary" : "objects"] = rows, ["offset"] = offset, ["limit"] = limit,
                ["next_offset"] = offset + rows.Count < rowCount ? new JValue(offset + rows.Count) : JValue.CreateNull(),
                ["complete"] = offset == 0 && rows.Count == rowCount,
                ["visibility_basis"] = "Rhino document visibility, including object/layer hiding; not pixel, frustum, clipping or occlusion proof.",
                ["limitations"] = new JArray("Top-level model objects only. scope=groups uses the distinct model-space members of the requested groups; other group relations do not expand the set. Block contents require result_mode=hierarchy.",
                    "Filters describe metadata, not architectural element identity. Scalar dictionary strings are not split into inferred lists.")
            };
            if (mode == "summary") { answer["result_mode"] = mode; answer["summary_count"] = rowCount; }
            if (Encoding.UTF8.GetByteCount(answer.ToString(Formatting.None)) > MaxBytes)
                return Error("observation_too_large", "Response exceeds 256 KiB; reduce limit, scope or geometry detail.");
            if (selected) answer["excluded_selected_count"] = all.Count(o => o.IsSelected(false) != 0) - candidates.Length;
            return QueryEvidence(answer, editor, snapshot, current, selected, insideWindow);
        }

        static JObject QueryEvidence(JObject result, JObject editor, string snapshot, bool current, bool selected, bool window)
        {
            result["snapshot"] = snapshot;
            result["editing"] = editor;
            if ((bool?)editor["stable"] != true)
            {
                result["membership_complete"] = false;
                result["page_complete"] = result["page_complete"] ?? result["complete"]?.DeepClone();
                result["complete"] = false;
                result["membership_limitation"] = "Editor working members can be observed, but original persistent group identity and ancestor membership are not fully verified. A current save target is not proof of its pre-edit GUID.";
            }
            if (current)
            {
                result["selection"] = selected ? "selected" : window ? "inside_window" : "all";
                result["visibility_basis"] = window
                    ? "Visible unlocked model objects whose world bounding boxes intersect the active model viewport frustum. Occlusion and clipping planes are not evaluated; bounding boxes can overinclude geometry."
                    : "Currently visible unlocked model objects, including off-screen objects. Object/layer hiding and locking apply; clipping planes and pixel occlusion do not change this scope.";
            }
            if (Encoding.UTF8.GetByteCount(result.ToString(Formatting.None)) > MaxBytes)
                return Error("observation_too_large", "Response including editor evidence exceeds 256 KiB; reduce limit or fields.");
            return result;
        }

        internal static string SnapshotToken(RhinoDoc doc, JObject request, RhinoObject[] objects, JObject editor)
        {
            var options = (JObject)request.DeepClone();
            foreach (string key in new[] { "offset", "limit", "face_offset", "face_limit", "expected_snapshot" }) options.Remove(key);
            var state = new JObject { ["document"] = doc.RuntimeSerialNumber, ["query"] = options, ["editing"] = editor,
                ["units"] = doc.ModelUnitSystem.ToString(), ["tolerance"] = doc.ModelAbsoluteTolerance,
                ["objects"] = new JArray(objects.OrderBy(o => o.Id).Select(ObjectStamp)),
                ["groups"] = new JArray(doc.Groups.Where(g => g != null && !g.IsDeleted).OrderBy(g => g.Id)
                    .Select(g => new JArray(g.Id.ToString(), g.Index, g.Name))),
                ["layers"] = new JArray(doc.Layers.Where(l => l != null && !l.IsDeleted)
                    .Select(l => new JArray(l.Id.ToString(), l.FullPath, l.IsVisible, l.IsLocked))),
                ["definitions"] = new JArray(doc.InstanceDefinitions.Where(d => d != null && !d.IsDeleted)
                    .OrderBy(d => d.Id).Select(d => new JObject { ["id"] = d.Id.ToString(), ["name"] = d.Name,
                        ["members"] = new JArray(d.GetObjects().OrderBy(o => o.Id).Select(ObjectStamp)) })) };
            if ((bool?)request["inside_window"] == true)
            {
                var view = doc.Views.ActiveView.ActiveViewport;
                if (!view.GetFrustum(out double left, out double right, out double bottom, out double top, out double near, out double far))
                    throw new ArgumentException("The active model viewport has no valid frustum.");
                state["view"] = new JArray(view.Id.ToString(), view.IsParallelProjection, view.CameraLocation.X, view.CameraLocation.Y, view.CameraLocation.Z,
                    view.CameraDirection.X, view.CameraDirection.Y, view.CameraDirection.Z,
                    view.CameraUp.X, view.CameraUp.Y, view.CameraUp.Z, left, right, bottom, top, near, far);
            }
            using (var sha = SHA256.Create())
                return Convert.ToHexString(sha.ComputeHash(Encoding.UTF8.GetBytes(state.ToString(Formatting.None)))).ToLowerInvariant();
        }

        static JArray ObjectStamp(RhinoObject obj) => new JArray(obj.Id.ToString(), obj.Geometry.DataCRC(0),
            obj.Attributes.ToJSON(new Rhino.FileIO.SerializationOptions()), obj.Visible, obj.IsLocked, obj.IsSelected(false));

        static bool Boolean(JObject request, string key)
        {
            if (request[key] == null) return false;
            if (request[key].Type != JTokenType.Boolean) throw new ArgumentException(key + " must be boolean.");
            return (bool)request[key];
        }

        static void ValidateFilters(JObject filters)
        {
            if (filters.Properties().Any(p => p.Name != "layer_paths" && p.Name != "object_types" && p.Name != "name_contains" && p.Name != "user_dictionary"))
                throw new ArgumentException("Filters support layer_paths, object_types, name_contains and user_dictionary only.");
            if (filters["layer_paths"] != null && (!(filters["layer_paths"] is JArray layers) || layers.Count == 0 || layers.Count > 64 ||
                layers.Any(v => v.Type != JTokenType.String || String.IsNullOrEmpty((string)v))))
                throw new ArgumentException("layer_paths must contain 1..64 exact full layer paths.");
            if (filters["name_contains"] != null && (filters["name_contains"].Type != JTokenType.String || ((string)filters["name_contains"]).Length > 256))
                throw new ArgumentException("name_contains must be a string of at most 256 characters.");
            if (filters["object_types"] != null && (!(filters["object_types"] is JArray types) || types.Count == 0 || types.Count > 32 ||
                types.Any(v => v.Type != JTokenType.String || !Enum.GetNames(typeof(ObjectType)).Contains((string)v, StringComparer.OrdinalIgnoreCase))))
                throw new ArgumentException("object_types must contain 1..32 Rhino object_type names from an observation.");
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
            if (filters["object_types"] is JArray types && !types.Values<string>().Contains(obj.ObjectType.ToString(), StringComparer.OrdinalIgnoreCase)) return false;
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
            if (value is Point3d point)
            {
                if ((budget.Nodes -= 3) < 0)
                    return new JObject { ["value_omitted"] = true, ["reason"] = "metadata_budget" };
                return new JObject { ["type"] = "Point3d", ["coordinates"] = Point(point) };
            }
            if (value is Plane plane)
            {
                if ((budget.Nodes -= 9) < 0)
                    return new JObject { ["value_omitted"] = true, ["reason"] = "metadata_budget" };
                return new JObject {
                    ["type"] = "Plane",
                    ["origin"] = Point(plane.Origin),
                    ["xaxis"] = new JArray(plane.XAxis.X, plane.XAxis.Y, plane.XAxis.Z),
                    ["yaxis"] = new JArray(plane.YAxis.X, plane.YAxis.Y, plane.YAxis.Z)
                };
            }
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
        internal static JObject IntersectionMetadata(RhinoObject obj)
        {
            var budget = new ValueBudget { Nodes = 2048, Characters = 16000 };
            var strings = obj.Attributes.GetUserStrings();
            var values = new JObject();
            if (strings != null)
                foreach (string key in strings.AllKeys.Take(64))
                {
                    if (key == null || (budget.Characters -= key.Length) < 0) break;
                    values[key] = SafeValue(strings[key], 0, budget);
                }
            return new JObject {
                ["attributes"] = new JObject {
                    ["name"] = SafeValue(obj.Attributes.Name, 0, budget), ["layer_index"] = obj.Attributes.LayerIndex,
                    ["material_index"] = obj.Attributes.MaterialIndex,
                    ["material_source"] = obj.Attributes.MaterialSource.ToString(),
                    ["color_source"] = obj.Attributes.ColorSource.ToString(),
                    ["object_color"] = obj.Attributes.ObjectColor.ToArgb(),
                    ["mode"] = obj.Attributes.Mode.ToString(),
                    ["user_strings"] = new JObject { ["values"] = values,
                        ["total_keys"] = strings?.Count ?? 0, ["truncated"] = (strings?.Count ?? 0) > values.Count },
                    ["projection"] = "Selected document attributes; custom geometry user data is not serialized."
                },
                ["user_dictionary"] = new JObject {
                    ["attributes"] = Dictionary(ExistingDictionary(obj.Attributes), budget),
                    ["geometry"] = Dictionary(ExistingDictionary(obj.Geometry), budget)
                }
            };
        }
        static JObject Bounds(BoundingBox b) => b.IsValid ? new JObject { ["min"] = Point(b.Min), ["max"] = Point(b.Max) } : null;
        static JObject Describe(RhinoDoc doc, RhinoObject obj, HashSet<Guid> matched, HashSet<Guid> visible,
            bool includeGeometry, ValueBudget budget, HashSet<string> fields, int faceOffset, int faceLimit,
            EditingContext.ObjectScope editing = null)
        {
            bool Want(string field, bool detail = false) => fields == null ? !detail || includeGeometry : fields.Contains(field);
            var geometry = obj.Geometry;
            var row = new JObject();
            if (Want("id")) row["id"] = obj.Id.ToString();
            if (Want("name")) row["name"] = obj.Name ?? "";
            if (Want("layer_path")) row["layer_path"] = doc.Layers.FindIndex(obj.Attributes.LayerIndex)?.FullPath;
            if (Want("object_type")) row["object_type"] = obj.ObjectType.ToString();
            if (Want("geometry_kind")) row["geometry_kind"] = geometry.GetType().Name;
            if (Want("geometry_crc")) row["geometry_crc"] = geometry.DataCRC(0);
            if (Want("visible")) row["visible"] = visible.Contains(obj.Id);
            if (Want("selected")) row["selected"] = obj.IsSelected(false) != 0;
            if (Want("hidden")) row["hidden"] = obj.IsHidden;
            if (Want("locked")) row["locked"] = obj.IsLocked;
            if (Want("bounds")) row["bounds"] = Bounds(geometry.GetBoundingBox(true));
            if (Want("groups"))
            {
                editing = editing ?? EditingContext.ObserveObjects(doc);
                var groups = new JArray();
                foreach (int index in (obj.Attributes.GetGroupList() ?? Array.Empty<int>()).Take(64))
                {
                    var group = doc.Groups[index];
                    groups.Add(GroupMembership(doc, group, matched, visible, editing));
                }
                row["groups"] = groups;
                row["groups_truncated"] = obj.Attributes.GroupCount > 64;
            }
            if (Want("user_dictionary")) row["user_dictionary"] = new JObject {
                ["attributes"] = Dictionary(ExistingDictionary(obj.Attributes), budget), ["geometry"] = Dictionary(ExistingDictionary(geometry), budget) };
            if (Want("geometry_valid", true)) row["geometry_valid"] = geometry.IsValid;
            if (geometry is Brep brep)
            {
                if (Want("solid", true)) row["solid"] = brep.IsSolid;
                if (Want("manifold", true)) row["manifold"] = brep.IsManifold;
                if (Want("face_count", true)) row["face_count"] = brep.Faces.Count;
                if (Want("faces", true))
                {
                    bool editable = geometry.IsValid && brep.IsSolid && brep.IsManifold && !obj.IsLocked && !obj.IsReference;
                    var faces = new JArray();
                    foreach (var face in brep.Faces.Skip(faceOffset).Take(faceLimit))
                    {
                        bool planar = face.TryGetPlane(out var plane, doc.ModelAbsoluteTolerance);
                        var normal = face.OrientationIsReversed ? -plane.Normal : plane.Normal;
                        bool adjacentPlanar = planar && face.AdjacentEdges().SelectMany(i => brep.Edges[i].AdjacentFaces()).Distinct()
                            .All(i => brep.Faces[i].IsPlanar(doc.ModelAbsoluteTolerance));
                        faces.Add(new JObject { ["face_index"] = face.FaceIndex, ["planar"] = planar,
                            ["plane_origin"] = planar ? Point(plane.Origin) : null,
                            ["normal"] = planar ? new JArray(normal.X, normal.Y, normal.Z) : null,
                            ["bounds"] = Bounds(face.GetBoundingBox(true)),
                            ["face_edit_supported"] = editable && adjacentPlanar });
                    }
                    // A face page always carries its source identity and version, even under field selection.
                    row["id"] = obj.Id.ToString();
                    row["geometry_crc"] = geometry.DataCRC(0);
                    row["face_count"] = brep.Faces.Count;
                    row["faces_truncated"] = faceOffset != 0 || faces.Count < brep.Faces.Count;
                    row["face_page"] = new JObject { ["offset"] = faceOffset, ["limit"] = faceLimit,
                        ["returned"] = faces.Count, ["next_offset"] = faceOffset + faces.Count < brep.Faces.Count
                            ? new JValue(faceOffset + faces.Count) : JValue.CreateNull(),
                        ["complete"] = faceOffset == 0 && faces.Count == brep.Faces.Count };
                    row["faces"] = faces;
                }
                if (Want("volume", true) && geometry.IsValid && brep.IsSolid)
                    using (var mass = VolumeMassProperties.Compute(brep)) row["volume"] = mass == null ? JValue.CreateNull() : new JValue(mass.Volume);
            }
            else if ((fields == null && includeGeometry) || Want("faces", true)) row["face_edit_supported"] = false;
            return row;
        }
        static JObject Error(string code, string message) => new JObject { ["status"] = "error", ["error_code"] = code, ["message"] = message };
    }
}
