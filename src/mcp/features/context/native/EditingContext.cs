using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.PlugIns;

namespace RhinoAlmondBridge
{
    /// <summary>
    /// Observes actual editor state on the UI thread, including when attached mid-edit.
    /// No commands, plugin loads, editor methods, or document writes are performed.
    /// The two private adapters are restricted to the inspected binary identities.
    /// </summary>
    public static class EditingContext
    {
        private sealed class Provider
        {
            internal readonly Guid Id;
            internal readonly string Name, FullName, Mvid, Hash;
            internal Provider(string id, string name, string fullName, string mvid, string hash)
            { Id = new Guid(id); Name = name; FullName = fullName; Mvid = mvid; Hash = hash; }
        }

        private static readonly Provider NewEditor = new Provider(
            "02844255-3ba6-4b94-af8a-b4e495baff71", "BlockEditNew",
            "BlockEditNew, Version=2.0.0.0, Culture=neutral, PublicKeyToken=null",
            "a20fdd51-e5f0-4a08-9f9d-5ca577771d23",
            "26FD17A77F2EB82ACC0CF8D5E3A6EA8248C242A461B4A0A334DF3E342477D8A2");
        private static readonly Provider BuiltIn = new Provider(
            "f2231a2f-66bf-4558-94ce-988c15aede65", "BlockEdit",
            "BlockEdit, Version=8.34.26223.11001, Culture=neutral, PublicKeyToken=null",
            "d45dba1e-9c65-4030-8054-a3da9b6d89dd",
            "B6B406319EBA9BAC67EF213BCEA0BE54C92A0F718A8C5F38887327821C30D97F");
        private static readonly HashSet<Assembly> VerifiedAssemblies = new HashSet<Assembly>();
        private const BindingFlags DeclaredFields = BindingFlags.Public | BindingFlags.NonPublic |
            BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly;

        public static JObject Observe(RhinoDoc doc)
        {
            var warnings = new JArray();
            var providers = new JArray();
            var evidence = new JObject { ["providers"] = providers };
            var reply = new JObject { ["mode"] = "unknown", ["target"] = null,
                ["stable"] = false, ["evidence"] = evidence, ["warnings"] = warnings };
            try
            {
                if (doc == null || RhinoApp.InvokeRequired || !doc.IsAvailable || doc.IsClosing || doc.IsOpening || RhinoApp.IsClosing)
                    throw new InvalidOperationException("The document must be available on Rhino's UI thread.");
                uint serial = doc.RuntimeSerialNumber;
                evidence["document_serial_number"] = serial;
                bool headless = doc.IsHeadless;
                ActiveSpace space = headless ? ActiveSpace.None : doc.ActiveSpace;
                evidence["active_space"] = headless ? "headless" : space.ToString();
                int commandCount = RhinoApp.InCommand;
                bool undo = doc.UndoActive, redo = doc.RedoActive, recordingUndo = doc.UndoRecordingIsActive;
                evidence["transient_state"] = new JObject { ["command_count"] = commandCount,
                    ["undo"] = undo, ["redo"] = redo, ["recording_undo"] = recordingUndo };
                if (commandCount > 0 || undo || redo || recordingUndo)
                    throw new InvalidOperationException("A command or Undo/Redo transition is in progress.");
                Assembly newAssembly = LoadedAssembly(NewEditor, providers);
                Assembly builtInAssembly = LoadedAssembly(BuiltIn, providers);
                JObject newer = newAssembly == null ? null : ReadNewEditor(newAssembly.ManifestModule, doc, evidence);
                JObject older = builtInAssembly == null ? null : ReadBuiltIn(builtInAssembly.ManifestModule, doc, evidence);
                if (newer != null && older != null)
                    throw new InvalidOperationException("Both block editor providers report an active editor for this document.");
                // Recheck provider loading every observation; attaching before plugin load is supported.
                if (!ReferenceEquals(newAssembly, LoadedAssembly(NewEditor, null)) ||
                    !ReferenceEquals(builtInAssembly, LoadedAssembly(BuiltIn, null)) ||
                    !doc.IsAvailable || doc.IsClosing || doc.RuntimeSerialNumber != serial)
                    throw new InvalidOperationException("The document or editor providers changed during observation.");
                var active = newer ?? older;
                if (active == null && !headless && space != ActiveSpace.ModelSpace && space != ActiveSpace.PageSpace)
                    throw new InvalidOperationException("The active viewport is not in a verified model or page space.");
                reply["mode"] = active == null ? "model" : (string)active["mode"];
                reply["target"] = active == null ? JValue.CreateNull() : active["target"];
                // Consumers use stable as permission to save/reconcile the whole model.
                // A known active editor remains observable, but cannot authorize that work.
                reply["stable"] = active == null;
            }
            catch (Exception ex)
            {
                warnings.Add("editing_context: " + ex.Message);
            }
            return reply;
        }

        private static Assembly LoadedAssembly(Provider provider, JArray evidence)
        {
            // These public APIs inspect installed/loaded plugins. GetPlugInObject would load one.
            var info = PlugIn.GetPlugInInfo(provider.Id);
            var matches = AppDomain.CurrentDomain.GetAssemblies()
                .Where(a => String.Equals(a.GetName().Name, provider.Name, StringComparison.Ordinal)).ToArray();
            if ((info == null || !info.IsLoaded) && matches.Length == 0)
            {
                if (evidence != null) evidence.Add(new JObject { ["provider"] = provider.Name,
                    ["state"] = info == null ? "not_installed" : "not_loaded" });
                return null;
            }
            var plugin = info != null && info.IsLoaded ? PlugIn.Find(provider.Id) : null;
            var assembly = plugin == null ? null : plugin.Assembly;
            if (assembly == null || matches.Length != 1 || !ReferenceEquals(matches[0], assembly))
                throw new InvalidOperationException(provider.Name + " loaded assembly could not be identified unambiguously.");
            ValidateAssembly(provider, assembly);
            if (evidence != null) evidence.Add(new JObject { ["provider"] = provider.Name,
                ["state"] = "loaded_verified", ["assembly"] = assembly.FullName,
                ["module_version_id"] = assembly.ManifestModule.ModuleVersionId.ToString(),
                ["adapter"] = "binary_identity_and_metadata_fields" });
            return assembly;
        }

        private static void ValidateAssembly(Provider provider, Assembly assembly)
        {
            if (!String.Equals(assembly.FullName, provider.FullName, StringComparison.Ordinal) ||
                assembly.ManifestModule.ModuleVersionId != new Guid(provider.Mvid))
                throw new InvalidOperationException(provider.Name + " version is not supported by the verified editor adapter.");
            lock (VerifiedAssemblies)
            {
                if (VerifiedAssemblies.Contains(assembly)) return;
                if (String.IsNullOrEmpty(assembly.Location))
                    throw new InvalidOperationException(provider.Name + " has no verifiable binary location.");
                using (var stream = File.OpenRead(assembly.Location))
                using (var sha = SHA256.Create())
                    if (!String.Equals(Convert.ToHexString(sha.ComputeHash(stream)), provider.Hash, StringComparison.Ordinal))
                        throw new InvalidOperationException(provider.Name + " binary hash does not match the inspected adapter.");
                VerifiedAssemblies.Add(assembly);
            }
        }

        private static JObject ReadNewEditor(Module module, RhinoDoc doc, JObject evidence)
        {
            var stack = ReadField(module, 0x04000185, null, typeof(IList)) as IList;
            if (stack == null) throw new InvalidOperationException("BlockEditNew editor stack is unavailable.");
            int count = stack.Count;
            if (count > 128) throw new InvalidOperationException("BlockEditNew editor stack exceeds the supported nesting limit.");
            var chain = new JArray();
            var snapshot = new object[count];
            JObject current = null;
            for (int i = 0; i < count; i++)
            {
                object editor = snapshot[i] = stack[i];
                if (editor == null) throw new InvalidOperationException("BlockEditNew editor stack contains a null entry.");
                var owner = ReadField(module, 0x0400018A, editor, typeof(RhinoDoc)) as RhinoDoc;
                if (owner == null) throw new InvalidOperationException("BlockEditNew editor has no owning document.");
                if (owner.RuntimeSerialNumber != doc.RuntimeSerialNumber) continue;
                int mode = Convert.ToInt32(ReadField(module, 0x04000189, editor, null));
                int type = editor.GetType().MetadataToken;
                if (mode == 2 && type == 0x02000045)
                    current = NewGroupTarget(module, editor, doc);
                else if (mode == 1 && type == 0x0200007B)
                    current = NewBlockTarget(module, editor, doc);
                else throw new InvalidOperationException("BlockEditNew editor mode and concrete type disagree.");
                chain.Add(current["target"].DeepClone());
            }
            if (stack.Count != count) throw new InvalidOperationException("BlockEditNew editor stack changed during observation.");
            for (int i = 0; i < count; i++)
                if (!ReferenceEquals(snapshot[i], stack[i])) throw new InvalidOperationException("BlockEditNew editor stack changed during observation.");
            evidence["blockeditnew_stack_depth"] = count;
            evidence["blockeditnew_document_chain"] = chain;
            return current;
        }

        private static JObject NewGroupTarget(Module module, object editor, RhinoDoc doc)
        {
            object info = ReadField(module, 0x04000193, editor, null);
            int index = (int)ReadField(module, 0x040001A8, info, typeof(int));
            string name = (string)ReadField(module, 0x040001A9, info, typeof(string));
            var members = ReadField(module, 0x040001AA, info, typeof(Guid[])) as Guid[];
            if (index < 0 || members == null)
                throw new InvalidOperationException("The group editor's original target identity is unavailable.");
            // The provider records an index, display label, and original members, but
            // never the group's persistent ID. A reused index cannot prove that ID.
            return Active("group", new JObject { ["provider"] = "BlockEditNew", ["group_index"] = index,
                ["group_id"] = null, ["editor_label"] = name == null || name.Length <= 160 ? name : name.Substring(0, 160),
                ["original_member_count"] = members.Length,
                ["identity_rule"] = "provider_original_index_and_members" });
        }

        private static JObject NewBlockTarget(Module module, object editor, RhinoDoc doc)
        {
            object info = ReadField(module, 0x04000216, editor, null);
            var instanceId = (Guid)ReadField(module, 0x04000234, info, typeof(Guid));
            int index = (int)ReadField(module, 0x04000235, info, typeof(int));
            var instance = ReadField(module, 0x04000236, info, typeof(InstanceObject)) as InstanceObject;
            string name = (string)ReadField(module, 0x04000239, info, typeof(string));
            var definition = index < 0 ? null : doc.InstanceDefinitions[index];
            if (instance == null || instanceId == Guid.Empty || instance.Id != instanceId || definition == null ||
                definition.IsDeleted || instance.InstanceDefinition == null || instance.InstanceDefinition.Id != definition.Id ||
                !String.Equals(definition.Name, name, StringComparison.Ordinal))
                throw new InvalidOperationException("The block editor target no longer resolves to its recorded instance and definition.");
            return Active("block", new JObject { ["provider"] = "BlockEditNew", ["instance_id"] = instanceId.ToString(),
                ["definition_id"] = definition.Id.ToString(), ["definition_index"] = index, ["definition_name"] = name });
        }

        private static JObject ReadBuiltIn(Module module, RhinoDoc doc, JObject evidence)
        {
            var editors = ReadField(module, 0x0400004B, null, typeof(IDictionary)) as IDictionary;
            if (editors == null) throw new InvalidOperationException("BlockEdit editor dictionary is unavailable.");
            object editor = editors.Contains(doc.RuntimeSerialNumber) ? editors[doc.RuntimeSerialNumber] : null;
            if (editor == null)
            {
                evidence["blockedit_document_state"] = "no_editor";
                return null;
            }
            if ((uint)ReadField(module, 0x04000054, editor, typeof(uint)) != doc.RuntimeSerialNumber)
                throw new InvalidOperationException("BlockEdit editor document identity disagrees with its dictionary.");
            bool running = (bool)ReadField(module, 0x04000052, editor, typeof(bool));
            evidence["blockedit_document_state"] = running ? "editing" : "inactive";
            if (!running) return null;
            var collections = ReadField(module, 0x04000042, null, typeof(IDictionary)) as IDictionary;
            object collection = collections != null && collections.Contains(doc.RuntimeSerialNumber)
                ? collections[doc.RuntimeSerialNumber] : null;
            if (collection == null || (uint)ReadField(module, 0x04000041, collection, typeof(uint)) != doc.RuntimeSerialNumber ||
                !(bool)ReadField(module, 0x0400003E, collection, typeof(bool)) ||
                (bool)ReadField(module, 0x04000040, collection, typeof(bool)))
                throw new InvalidOperationException("BlockEdit is changing or has no prepared edit collection.");
            Guid itemId = (Guid)ReadField(module, 0x04000045, collection, typeof(Guid));
            object root = ReadField(module, 0x04000047, collection, null);
            var items = new Stack<object>();
            var seen = new HashSet<object>();
            if (root != null) items.Push(root);
            object selected = null;
            while (items.Count > 0)
            {
                object item = items.Pop();
                if (!seen.Add(item) || seen.Count > 10000)
                    throw new InvalidOperationException("BlockEdit item tree is cyclic or exceeds the supported limit.");
                if ((Guid)ReadField(module, 0x0400002E, item, typeof(Guid)) == itemId)
                {
                    if (selected != null) throw new InvalidOperationException("BlockEdit current item identity is ambiguous.");
                    selected = item;
                }
                var children = ReadField(module, 0x0400003C, item, typeof(IEnumerable)) as IEnumerable;
                if (children != null) foreach (object child in children) if (child != null) items.Push(child);
            }
            if (selected == null || (uint)ReadField(module, 0x0400002C, selected, typeof(uint)) != doc.RuntimeSerialNumber)
                throw new InvalidOperationException("BlockEdit current item cannot be resolved for this document.");
            Guid referenceId = (Guid)ReadField(module, 0x04000030, selected, typeof(Guid));
            Guid definitionId = (Guid)ReadField(module, 0x04000037, selected, typeof(Guid));
            var definition = doc.InstanceDefinitions.Find(definitionId, true);
            if (referenceId == Guid.Empty || definition == null || definition.IsDeleted ||
                !(bool)ReadField(module, 0x04000052, editor, typeof(bool)) ||
                (Guid)ReadField(module, 0x04000045, collection, typeof(Guid)) != itemId)
                throw new InvalidOperationException("BlockEdit target changed or its definition is unavailable.");
            return Active("block", new JObject { ["provider"] = "BlockEdit", ["instance_id"] = referenceId.ToString(),
                ["definition_id"] = definitionId.ToString(), ["definition_index"] = definition.Index,
                ["definition_name"] = definition.Name, ["edit_item_id"] = itemId.ToString() });
        }

        private static object ReadField(Module module, int token, object instance, Type expectedType)
        {
            var field = module.ResolveField(token);
            if (field == null || field.IsStatic != (instance == null) ||
                (instance != null && !field.DeclaringType.IsInstanceOfType(instance)) ||
                (expectedType != null && !expectedType.IsAssignableFrom(field.FieldType)))
                throw new InvalidOperationException("The verified editor field shape no longer matches its adapter.");
            return field.GetValue(instance);
        }

        private static JObject Active(string mode, JObject target)
        {
            return new JObject { ["mode"] = mode, ["target"] = target };
        }
    }
}
