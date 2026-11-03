using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;

namespace RhinoAlmondBridge
{
    public static partial class EditingContext
    {
        // The verified provider's save-member algorithm (method 0x06000309) reads
        // these sets and resolves current document objects. Never invoke provider
        // methods, use visibility as ownership, or reuse entry-time object counts.
        public sealed class ObjectScope
        {
            public JObject State;
            public readonly List<GroupScope> Groups = new List<GroupScope>();
            public RhinoObject[] CurrentObjects;
            public bool MembersKnown;
            public string Limitation;
        }

        public sealed class GroupScope
        {
            public int Index;
            public string Label;
            public RhinoObject[] Objects;
            public bool Current;
        }

        public static ObjectScope ObserveObjects(RhinoDoc doc)
        {
            var result = new ObjectScope { State = Observe(doc), CurrentObjects = Array.Empty<RhinoObject>() };
            if ((string)result.State["mode"] == "model" && (bool?)result.State["stable"] == true)
            { result.MembersKnown = true; return result; }
            try
            {
                if (!CanObserve(result.State)) throw new InvalidOperationException("The editor state is not verified.");
                if ((string)result.State["target"]?["provider"] != "BlockEditNew")
                    throw new InvalidOperationException("This editor's working-object ownership adapter is unavailable.");
                var assembly = LoadedAssembly(NewEditor, null);
                var module = assembly.ManifestModule;
                var stack = (IList)ReadField(module, 0x04000185, null, typeof(IList));
                var editors = stack.Cast<object>().Where(e =>
                    ((RhinoDoc)ReadField(module, 0x0400018A, e, typeof(RhinoDoc))).RuntimeSerialNumber == doc.RuntimeSerialNumber).ToArray();
                if (editors.Length == 0) throw new InvalidOperationException("The active editor disappeared.");
                for (int level = 0; level < editors.Length; level++)
                {
                    object editor = editors[level];
                    bool group = editor.GetType().MetadataToken == 0x02000045;
                    object manager = ReadField(module, group ? 0x04000198 : 0x0400021B, editor, null);
                    var tracked = (HashSet<Guid>)ReadField(module, 0x040001CF, manager, typeof(HashSet<Guid>));
                    var excludedA = (HashSet<Guid>)ReadField(module, 0x040001D0, manager, typeof(HashSet<Guid>));
                    var excludedB = (HashSet<Guid>)ReadField(module, 0x040001D1, manager, typeof(HashSet<Guid>));
                    if (tracked == null || excludedA == null || excludedB == null || tracked.Count > 100000)
                        throw new InvalidOperationException("The provider's working-member sets are unavailable or exceed the observation budget.");
                    var members = tracked.Where(id => !excludedA.Contains(id) && !excludedB.Contains(id))
                        .Select(id => doc.Objects.FindId(id))
                        .Where(o => o != null && !o.IsDeleted && !o.IsInstanceDefinitionGeometry && o.Attributes.Space != ActiveSpace.PageSpace)
                        .OrderBy(o => o.Id).ToArray();
                    bool current = level == editors.Length - 1;
                    if (current) result.CurrentObjects = members;
                    if (group)
                    {
                        object info = ReadField(module, 0x04000193, editor, null);
                        result.Groups.Add(new GroupScope {
                            Index = (int)ReadField(module, 0x040001A8, info, typeof(int)),
                            Label = (string)ReadField(module, 0x040001A9, info, typeof(string)),
                            Objects = members, Current = current });
                    }
                }
                if (!JToken.DeepEquals(result.State, Observe(doc)))
                    throw new InvalidOperationException("The editor changed while reading working members.");
                result.MembersKnown = true;
                result.Limitation = "Working IDs resolve current model-space objects. No original-to-working identity mapping is inferred. Ancestor editors are incomplete while a child is open.";
            }
            catch (Exception error)
            {
                result.Groups.Clear(); result.CurrentObjects = Array.Empty<RhinoObject>();
                result.MembersKnown = false; result.Limitation = error.Message;
            }
            result.State["working_scope"] = new JObject {
                ["available"] = result.MembersKnown,
                ["current_member_count"] = result.MembersKnown ? new JValue(result.CurrentObjects.Length) : JValue.CreateNull(),
                ["current_object_ids"] = result.MembersKnown ? new JArray(result.CurrentObjects.Take(512).Select(o => o.Id.ToString())) : null,
                ["current_ids_truncated"] = result.CurrentObjects.Length > 512,
                ["membership_snapshot"] = result.MembersKnown ? Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(
                    System.Text.Encoding.UTF8.GetBytes(String.Join("|", result.CurrentObjects.Select(o => o.Id.ToString())) + "\n" +
                        String.Join("\n", result.Groups.Select(g => g.Index + ":" + g.Label + ":" +
                            String.Join("|", g.Objects.Select(o => o.Id.ToString()))))))).ToLowerInvariant() : null,
                ["basis"] = "verified provider save-member sets and live document lookup",
                ["limitation"] = result.Limitation };
            return result;
        }

        public static RhinoObject[] GroupObjects(RhinoDoc doc, Group group, ObjectScope scope, out bool complete, out string basis)
        {
            complete = (bool?)scope.State["stable"] == true;
            basis = "document_group_table";
            if (complete) return doc.Groups.GroupMembers(group.Index) ?? Array.Empty<RhinoObject>();
            var editing = scope.Groups.SingleOrDefault(g => g.Index == group.Index);
            if (editing != null && String.Equals(editing.Label, group.Name, StringComparison.Ordinal))
            {
                // This is the current table slot used by the provider when saving.
                // The provider does not retain the original persistent group GUID.
                basis = editing.Current ? "editor_current_save_target" : "ancestor_editor_partial";
                complete = false;
                return editing.Objects;
            }
            // Unrelated membership may also be affected by a nested edit. Retain
            // observed relations, but never certify a complete/empty original group.
            basis = "document_group_table_during_edit_incomplete";
            return doc.Groups.GroupMembers(group.Index) ?? Array.Empty<RhinoObject>();
        }
    }
}
