using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.Geometry;
using RhinoAlmondBridge;

namespace AlmondScriptUndoTests
{
    // The public native boundary observes real disposable groups, never a simulated attribute ledger.
    public static class ComponentHierarchyTests
    {
        public static string RunAll(string directory)
        {
            Directory.CreateDirectory(directory);
            var results = new List<string>();
            Run(results, directory, "existing group registration never stamps or duplicates architectural objects", doc => {
                Guid a = doc.Objects.AddPoint(Point3d.Origin), b = doc.Objects.AddPoint(new Point3d(10,0,0));
                var attrs = doc.Objects.FindId(a).Attributes.Duplicate(); attrs.SetUserString("user:note", "keep");
                doc.Objects.ModifyAttributes(a, attrs, true);
                int ordinary = doc.Groups.Add("Panel", new[] {a,b});
                var groups = doc.Objects.FindId(a).Attributes.GetGroupList();
                var created = Success(ComponentRegistry.Handle(doc, Request(doc, "upsert", "panel", new[] {a,b}, doc.Groups[ordinary].Id)));
                Check((string)created["rhino_group_id"] == doc.Groups[ordinary].Id.ToString("D"), "Registration duplicated the supplied group.");
                Check(doc.Groups.Count(g => !g.IsDeleted) == 1 && doc.Objects.FindId(a).Attributes.GetUserStrings().Count == 1 &&
                    doc.Objects.FindId(a).Attributes.GetUserString("user:note") == "keep" && doc.Objects.FindId(b).Attributes.GetUserStrings().Count == 0,
                    "Registration wrote management attributes or changed unrelated attributes.");
                Check(doc.Objects.FindId(a).Attributes.GetGroupList().SequenceEqual(groups), "Registration changed group order.");
            });
            Run(results, directory, "manual membership and group names are truth and inspect is read-only", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin), b=doc.Objects.AddPoint(new Point3d(5,0,0));
                int group=doc.Groups.Add("Panel", new[]{a});
                Success(ComponentRegistry.Handle(doc, Request(doc,"upsert","panel",new[]{a},doc.Groups[group].Id)));
                var attrs=doc.Objects.FindId(b).Attributes.Duplicate(); attrs.AddToGroup(group); doc.Objects.ModifyAttributes(b,attrs,true);
                attrs=doc.Objects.FindId(a).Attributes.Duplicate(); attrs.RemoveFromGroup(group); doc.Objects.ModifyAttributes(a,attrs,true);
                doc.Groups.ChangeGroupName(group,"User edited name");
                uint next=doc.NextUndoRecordSerialNumber; bool modified=doc.Modified;
                var snapshot=Success(ComponentRegistry.Handle(doc,Request(doc,"inspect","panel",null,doc.Groups[group].Id)));
                Check(snapshot["object_ids"].Values<string>().SequenceEqual(new[]{b.ToString("D")}) && (string)snapshot["name"]=="User edited name", "Inspection restored stale membership or name.");
                Check(next==doc.NextUndoRecordSerialNumber && modified==doc.Modified && doc.Objects.FindId(b).Attributes.GetUserStrings().Count==0,
                    "Inspection changed native document state.");
            });
            Run(results, directory, "one invalid legacy host never blocks an unrelated semantic group", doc => {
                Guid bad=doc.Objects.AddPoint(Point3d.Origin), valid=doc.Objects.AddPoint(new Point3d(20,0,0));
                var attrs=doc.Objects.FindId(bad).Attributes.Duplicate(); attrs.SetUserString("almond:component_record","invalid JSON");
                attrs.SetUserString("almond:component_id","stale"); doc.Objects.ModifyAttributes(bad,attrs,true);
                int group=doc.Groups.Add("Panel",new[]{valid});
                Success(ComponentRegistry.Handle(doc,Request(doc,"upsert","panel",new[]{valid},doc.Groups[group].Id)));
                var request=new JObject{["action"]="inspect_many",["expected_model_path"]=doc.Path,["component_ids"]=new JArray("panel")};
                var result=ComponentRegistry.Handle(doc,request);
                Check((string)result["status"]=="success" && ((JArray)result["components"]).Count==1 && ((JArray)result["problems"]).Count==1,
                    "An invalid legacy record blocked unrelated observation.");
                Check(doc.Objects.FindId(bad).Attributes.GetUserString("almond:component_record")=="invalid JSON", "Legacy attributes were silently deleted.");
            }, legacyArchive: true);
            Run(results, directory, "nested meaning uses actual groups without rewriting direct ownership or group order", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin), b=doc.Objects.AddPoint(new Point3d(30,0,0));
                int leaf=doc.Groups.Add("Leaf",new[]{a}), root=doc.Groups.Add("Root",new[]{a,b});
                var order=doc.Objects.FindId(a).Attributes.GetGroupList();
                Success(ComponentRegistry.Handle(doc,Request(doc,"upsert","leaf",new[]{a},doc.Groups[leaf].Id,"Leaf")));
                var parent=Request(doc,"upsert","root",new[]{b},doc.Groups[root].Id,"Root"); parent["child_component_ids"]=new JArray("leaf");
                var snapshot=Success(ComponentRegistry.Handle(doc,parent));
                Check(((JArray)snapshot["objects"]).Count==1 && ((JArray)snapshot["effective_objects"]).Count==2,
                    "Nested snapshot confused direct and effective group members.");
                Check(snapshot["effective_objects"].Any(o=>(string)o["rhino_guid"]==a.ToString("D")&&(string)o["component_id"]=="leaf"), "Derived child ownership was lost.");
                Check(doc.Objects.FindId(a).Attributes.GetGroupList().SequenceEqual(order) && doc.Objects.FindId(a).Attributes.GetUserStrings().Count==0,
                    "Semantic hierarchy altered ordinary groups or stamped members.");
            });
            Run(results, directory, "explicit Scene root scope includes descendants without inheriting another Scene", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin), b=doc.Objects.AddPoint(new Point3d(30,0,0));
                int leaf=doc.Groups.Add("Leaf",new[]{a}), root=doc.Groups.Add("Root",new[]{a,b});
                var child=Request(doc,"upsert","leaf",new[]{a},doc.Groups[leaf].Id,"Leaf"); child["scene_ids"]=new JArray("scene-a");
                Success(ComponentRegistry.Handle(doc,child));
                var parent=Request(doc,"upsert","root",new[]{b},doc.Groups[root].Id,"Root");
                parent["scene_ids"]=new JArray("scene-b"); parent["child_component_ids"]=new JArray("leaf");
                Success(ComponentRegistry.Handle(doc,parent));
                var response=ComponentRegistry.Handle(doc,new JObject{["action"]="inspect_many",["expected_model_path"]=doc.Path,
                    ["component_ids"]=new JArray("root","leaf"),["scene_id"]="scene-b"});
                Check((string)response["status"]=="success"&&((JArray)response["components"]).Count==2,
                    "Native Scene filtering discarded an explicitly requested descendant.");
                var observed=response["components"].Single(item=>(string)item["component_id"]=="leaf");
                Check(observed["scene_ids"].Values<string>().SequenceEqual(new[]{"scene-a"}),"Parent Scene context was inherited by the child.");
                response=ComponentRegistry.Handle(doc,new JObject{["action"]="inspect_many",["expected_model_path"]=doc.Path,
                    ["component_ids"]=new JArray(),["scene_id"]="scene-b",["discover_scene"]=true});
                Check((string)response["status"]=="success"&&((JArray)response["components"]).Count==2,
                    "Native-only Scene discovery omitted a new root or its differently scoped child.");
                response=ComponentRegistry.Handle(doc,new JObject{["action"]="inspect_many",["expected_model_path"]=doc.Path,
                    ["component_ids"]=new JArray("leaf"),["scene_id"]="scene-b"});
                Check((string)response["status"]=="success"&&((JArray)response["components"]).Count==1&&
                    (string)response["components"][0]["component_id"]=="leaf","An explicit ID scope broadened into another Scene root.");
            });
            Run(results, directory, "unregister Undo Redo preserves the ordinary group and all geometry", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin); int group=doc.Groups.Add("Panel",new[]{a}); Guid gid=doc.Groups[group].Id;
                Success(ComponentRegistry.Handle(doc,Request(doc,"upsert","panel",new[]{a},gid)));
                var removed=ComponentRegistry.Handle(doc,Request(doc,"unregister","panel",null,gid)); Check((string)removed["status"]=="success",removed.ToString());
                Check((string)Success(ComponentRegistry.Handle(doc,Request(doc,"inspect","panel",null,gid)))["registration_status"]=="unregistered","Unregister remained active.");
                UndoRedo(doc,false);
                Check((string)Success(ComponentRegistry.Handle(doc,Request(doc,"inspect","panel",null,gid)))["registration_status"]=="registered","Undo did not restore meaning binding.");
                UndoRedo(doc,true);
                Check((string)Success(ComponentRegistry.Handle(doc,Request(doc,"inspect","panel",null,gid)))["registration_status"]=="unregistered","Redo did not remove meaning binding.");
                Check(doc.Objects.FindId(a)!=null && doc.Groups.GroupMembers(group).Length==1 && doc.Objects.FindId(a).Attributes.GetUserStrings().Count==0,
                    "Unregistration changed the ordinary group or geometry.");
            });
            Run(results, directory, "non-Undo group-table deletion stays missing and explicit Undelete restores the same binding", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin); int group=doc.Groups.Add("Panel",new[]{a}); Guid gid=doc.Groups[group].Id;
                Success(ComponentRegistry.Handle(doc,Request(doc,"upsert","panel",new[]{a},gid)));
                var deleted=new ScriptExecutor().ExecuteAction(doc,()=>{Check(doc.Groups.Delete(group),"Group delete failed.");return null;});
                Check(deleted.Status=="success",deleted.Message);
                var missing=Success(ComponentRegistry.Handle(doc,Request(doc,"inspect","panel",null,gid)));
                Check((string)missing["availability"]=="missing_group"&&((JArray)missing["objects"]).Count==0,"Inspection recreated a missing group.");
                Check(doc.Groups.Undelete(group),"Explicit fixture Undelete failed.");
                Check((string)Success(ComponentRegistry.Handle(doc,Request(doc,"inspect","panel",null,gid)))["availability"]=="present","Explicit Undelete lost the persistent group binding.");
            });
            Run(results, directory, "actual member deletion and native Undo restore the same semantic binding", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin); int group=doc.Groups.Add("Panel",new[]{a}); Guid gid=doc.Groups[group].Id;
                Success(ComponentRegistry.Handle(doc,Request(doc,"upsert","panel",new[]{a},gid)));
                var deleted=new ScriptExecutor().ExecuteAction(doc,()=>{Check(doc.Objects.Delete(a,true),"Object deletion failed.");return null;});
                Check(deleted.Status=="success",deleted.Message);
                Check(((JArray)Success(ComponentRegistry.Handle(doc,Request(doc,"inspect","panel",null,gid)))["objects"]).Count==0,
                    "Inspection recreated a deleted member.");
                UndoRedo(doc,false);
                Check(Success(ComponentRegistry.Handle(doc,Request(doc,"inspect","panel",null,gid)))["object_ids"].Values<string>().SequenceEqual(new[]{a.ToString("D")}),
                    "Object Undo lost membership or semantic identity.");
            });
            Run(results, directory, "registration Undo restores original membership and name collisions refuse before mutation", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin);
                var serialization=new Rhino.FileIO.SerializationOptions{WriteUserData=true};
                string originalAttrs=doc.Objects.FindId(a).Attributes.ToJSON(serialization);uint originalCrc=doc.Objects.FindId(a).Geometry.DataCRC(0);
                var request=Request(doc,"upsert","panel",new[]{a},Guid.Empty); request.Remove("rhino_group_id");
                var created=Success(ComponentRegistry.Handle(doc,request)); Guid gid=Guid.Parse((string)created["rhino_group_id"]);
                UndoRedo(doc,false);
                var inactive=Success(ComponentRegistry.Handle(doc,Request(doc,"inspect","panel",null,gid)));
                var group=doc.Groups.FindId(gid);
                Check((string)inactive["registration_status"]=="unregistered"&&group!=null&&!doc.Groups.IsDeleted(group.Index)&&
                    doc.Groups.GroupMembers(group.Index).Length==0&&doc.Objects.FindId(a).Attributes.ToJSON(serialization)==originalAttrs&&
                    doc.Objects.FindId(a).Geometry.DataCRC(0)==originalCrc,
                    "Registration Undo did not restore original object attributes while retaining the empty native group-table entry.");
                string registry=ComponentSemanticRegistry.Export(doc);uint next=doc.NextUndoRecordSerialNumber;int count=doc.Groups.Count;bool modified=doc.Modified;
                var collision=(JObject)request.DeepClone();collision["component_id"]="other-panel";
                var rejected=ComponentRegistry.Handle(doc,collision);
                Check((string)rejected["status"]=="error"&&(string)rejected["error_code"]=="component_name_collision"&&(bool?)rejected["mutation_applied"]==false&&
                    ComponentSemanticRegistry.Export(doc)==registry&&doc.NextUndoRecordSerialNumber==next&&doc.Groups.Count==count&&doc.Modified==modified&&
                    doc.Objects.FindId(a).Attributes.ToJSON(serialization)==originalAttrs,"Name collision mutated the document or silently suffixed a duplicate group.");
                UndoRedo(doc,true);
                Check((string)Success(ComponentRegistry.Handle(doc,Request(doc,"inspect","panel",null,gid)))["registration_status"]=="registered",
                    "Registration Redo failed over the retained ordinary group.");
                Check(doc.Groups.GroupMembers(group.Index).Select(o=>o.Id).SequenceEqual(new[]{a})&&doc.Objects.FindId(a).Geometry.DataCRC(0)==originalCrc,
                    "Registration Redo did not restore group membership and meaning together.");
            });
            Run(results, directory, "semantic map serializes without changing object attributes", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin); int group=doc.Groups.Add("Panel",new[]{a});
                Success(ComponentRegistry.Handle(doc,Request(doc,"upsert","panel",new[]{a},doc.Groups[group].Id)));
                string exported=ComponentSemanticRegistry.Export(doc);
                ComponentSemanticRegistry.Import(doc,exported);
                Check(ComponentSemanticRegistry.Export(doc)==exported && doc.Objects.FindId(a).Attributes.GetUserStrings().Count==0,
                    "Registry serialization changed semantic identity or wrote an object attribute.");
                Check(doc.WriteFile(doc.Path,new Rhino.FileIO.FileWriteOptions{SuppressDialogBoxes=true}),"Save failed.");
                using(var reopened=RhinoDoc.OpenHeadless(doc.Path))
                    Success(ComponentRegistry.Handle(reopened,Request(reopened,"inspect","panel",null,doc.Groups[group].Id)));
            });
            Run(results, directory, "empty archived registry accepts missing DB identities but never resurrects a tombstone", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin); int group=doc.Groups.Add("Panel",new[]{a}); Guid gid=doc.Groups[group].Id;
                ComponentSemanticRegistry.Import(doc,"{\"version\":1,\"records\":{}}");
                var seed=Request(doc,"inspect","panel",null,gid);
                seed["registrations"]=new JArray(new JObject{["component_id"]="panel",["rhino_group_id"]=gid.ToString("D"),
                    ["name"]="Panel",["scene_ids"]=new JArray("inside"),["child_component_ids"]=new JArray()});
                Check((string)Success(ComponentRegistry.Handle(doc,seed))["availability"]=="present","Archived empty registry blocked DB identity recovery.");
                SuccessStatus(ComponentRegistry.Handle(doc,Request(doc,"unregister","panel",null,gid)));
                string archive=ComponentSemanticRegistry.Export(doc); ComponentSemanticRegistry.Import(doc,archive);
                Check((string)Success(ComponentRegistry.Handle(doc,seed))["registration_status"]=="unregistered","A cached DB seed resurrected explicit unregister.");
                Check(doc.Objects.FindId(a).Attributes.GetUserStrings().Count==0,"DB identity recovery wrote object attributes.");
            });
            Run(results, directory, "archive export defers legacy object observation until a stable registry request", doc => {
                Guid bad=doc.Objects.AddPoint(Point3d.Origin),valid=doc.Objects.AddPoint(new Point3d(20,0,0));
                var attrs=doc.Objects.FindId(bad).Attributes.Duplicate(); attrs.SetUserString("almond:component_record","invalid JSON");
                doc.Objects.ModifyAttributes(bad,attrs,true);
                int group=doc.Groups.Add("Panel",new[]{valid}); Guid gid=doc.Groups[group].Id;
                uint next=doc.NextUndoRecordSerialNumber; bool modified=doc.Modified;
                string pending=ComponentSemanticRegistry.Export(doc); ComponentSemanticRegistry.Import(doc,pending);
                Check(next==doc.NextUndoRecordSerialNumber&&modified==doc.Modified,"Archive helper changed the native document.");
                Success(ComponentRegistry.Handle(doc,Request(doc,"upsert","panel",new[]{valid},gid)));
                var reply=ComponentRegistry.Handle(doc,new JObject{["action"]="inspect_many",["expected_model_path"]=doc.Path,["component_ids"]=new JArray("panel")});
                SuccessStatus(reply);
                Check(((JArray)reply["problems"]).Count==1&&(string)reply["problems"][0]["code"]=="invalid_legacy_record",
                    "Save-time export consumed legacy observation outside the stable request boundary.");
                Check(doc.Objects.FindId(bad).Attributes.GetUserString("almond:component_record")=="invalid JSON","Archive helper changed legacy metadata.");
            },legacyArchive:true);
            Run(results, directory, "archive import insert template reference and unknown modes preserve current meaning", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin);int group=doc.Groups.Add("Panel",new[]{a});Guid gid=doc.Groups[group].Id;
                Success(ComponentRegistry.Handle(doc,Request(doc,"upsert","panel",new[]{a},gid)));
                SuccessStatus(ComponentRegistry.Handle(doc,Request(doc,"unregister","panel",null,gid)));
                string before=ComponentSemanticRegistry.Export(doc);
                var excluded=new Rhino.FileIO.FileReadOptions[]{null,new Rhino.FileIO.FileReadOptions{OpenMode=false},
                    new Rhino.FileIO.FileReadOptions{OpenMode=true,ImportMode=true},new Rhino.FileIO.FileReadOptions{OpenMode=true,InsertMode=true},
                    new Rhino.FileIO.FileReadOptions{OpenMode=true,NewMode=true},new Rhino.FileIO.FileReadOptions{OpenMode=true,ImportReferenceMode=true}};
                foreach(var options in excluded)
                {
                    ComponentSemanticRegistry.Read(doc,null,options);
                    Check(ComponentSemanticRegistry.Export(doc)==before,"A non-Open archive changed this document's registry/tombstone.");
                }
                bool needsArchive=false;
                try{ComponentSemanticRegistry.Read(doc,null,new Rhino.FileIO.FileReadOptions{OpenMode=true});}
                catch(ArgumentNullException){needsArchive=true;}
                Check(needsArchive,"Normal Open did not reach the archive reader.");
            });
            Run(results, directory, "oversized observed registration cannot poison the next document save", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin);int group=doc.Groups.Add("Panel",new[]{a});Guid gid=doc.Groups[group].Id;
                Success(ComponentRegistry.Handle(doc,Request(doc,"upsert","panel",new[]{a},gid)));
                string before=null;
                for(int index=0;index<3;index++)
                {
                    Guid member=doc.Objects.AddPoint(new Point3d(20+index,0,0));int seedGroup=doc.Groups.Add("Seed "+index,new[]{member});
                    var seed=new JObject{["component_id"]="seed-"+index,["rhino_group_id"]=doc.Groups[seedGroup].Id.ToString("D"),
                        ["name"]=new string('x',1500000),["scene_ids"]=new JArray("inside"),["child_component_ids"]=new JArray()};
                    before=ComponentSemanticRegistry.Export(doc);
                    var reply=ComponentRegistry.Handle(doc,new JObject{["action"]="inspect_many",["expected_model_path"]=doc.Path,
                        ["component_ids"]=new JArray("panel"),["registrations"]=new JArray(seed)});
                    SuccessStatus(reply);
                    string after=ComponentSemanticRegistry.Export(doc);
                    if(index<2)Check(after.Length>before.Length,"Valid bounded seed was discarded.");
                    else Check(after==before&&reply["problems"].Any(problem=>(string)problem["code"]=="registry_budget_exceeded"),
                        "Oversized read-only seed changed the saveable document registry.");
                }
                Check(doc.WriteFile(doc.Path,new Rhino.FileIO.FileWriteOptions{SuppressDialogBoxes=true}),"A rejected oversized seed poisoned the next save.");
            });
            Run(results, directory, "DB recovery of a conflicted legacy handle retains explicit uncertainty", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin),b=doc.Objects.AddPoint(new Point3d(20,0,0));
                int first=doc.Groups.Add("Panel",new[]{a}),second=doc.Groups.Add("Other",new[]{b});
                var seed=new JObject{["component_id"]="panel",["rhino_group_id"]=doc.Groups[first].Id.ToString("D"),
                    ["name"]="Panel",["scene_ids"]=new JArray("inside"),["child_component_ids"]=new JArray()};
                var conflicting=(JObject)seed.DeepClone();conflicting["rhino_group_id"]=doc.Groups[second].Id.ToString("D");
                var attrs=doc.Objects.FindId(a).Attributes.Duplicate();attrs.SetUserString("almond:component_record",seed.ToString());doc.Objects.ModifyAttributes(a,attrs,true);
                attrs=doc.Objects.FindId(b).Attributes.Duplicate();attrs.SetUserString("almond:component_record",conflicting.ToString());doc.Objects.ModifyAttributes(b,attrs,true);
                var reply=ComponentRegistry.Handle(doc,new JObject{["action"]="inspect_many",["expected_model_path"]=doc.Path,
                    ["component_ids"]=new JArray("panel"),["registrations"]=new JArray(seed)});
                SuccessStatus(reply);
                Check(((JArray)reply["components"]).Count==1&&reply["problems"].Any(problem=>(string)problem["component_id"]=="panel"&&
                    (string)problem["code"]=="legacy_record_conflict"),"Recovered legacy identity silently discarded its conflict evidence.");
                Check(doc.Objects.FindId(a).Attributes.GetUserString("almond:component_record")==seed.ToString()&&
                    doc.Objects.FindId(b).Attributes.GetUserString("almond:component_record")==conflicting.ToString(),"Conflict recovery rewrote legacy attributes.");
            },legacyArchive:true);
            Run(results, directory, "presence proof separates deleted objects from live detached Scene candidates", doc => {
                Guid a=doc.Objects.AddPoint(Point3d.Origin),b=doc.Objects.AddPoint(new Point3d(10,0,0)),c=doc.Objects.AddPoint(new Point3d(20,0,0));
                int group=doc.Groups.Add("Panel",new[]{a,b,c}); Guid gid=doc.Groups[group].Id;
                Success(ComponentRegistry.Handle(doc,Request(doc,"upsert","panel",new[]{a,b,c},gid)));
                Check(doc.Objects.Delete(a,true),"Fixture object deletion failed.");
                var attrs=doc.Objects.FindId(b).Attributes.Duplicate(); attrs.RemoveFromGroup(group); attrs.Name="Detached but alive";
                Check(doc.Objects.ModifyAttributes(b,attrs,true),"Fixture detach failed.");
                uint next=doc.NextUndoRecordSerialNumber; bool modified=doc.Modified;
                var reply=ComponentRegistry.Handle(doc,new JObject{["action"]="inspect_many",["expected_model_path"]=doc.Path,
                    ["component_ids"]=new JArray("panel"),["prior_object_ids"]=new JArray(a.ToString("D"),b.ToString("D"),c.ToString("D"))});
                SuccessStatus(reply);
                Check((bool)reply["presence_complete"]&&reply["absent_object_ids"].Values<string>().SequenceEqual(new[]{a.ToString("D")}),"Deletion proof is incomplete or claims a living object.");
                Check(((JArray)reply["detached_objects"]).Count==1&&(string)reply["detached_objects"][0]["rhino_guid"]==b.ToString("D")&&
                    (string)reply["detached_objects"][0]["name"]=="Detached but alive","Live detached object observation was omitted.");
                Check(next==doc.NextUndoRecordSerialNumber&&modified==doc.Modified&&doc.Objects.FindId(b).Attributes.GetUserStrings().Count==0,
                    "Presence observation mutated geometry, attributes or Undo.");
            });
            string report = String.Join("\n", results);
            if (results.Any(line => line.StartsWith("FAIL "))) throw new InvalidOperationException(report);
            return report + "\nPASS: " + results.Count + "/" + results.Count + " Component hierarchy cases.";
        }
        private static JObject Request(RhinoDoc doc,string action,string id,Guid[] objects,Guid group,string name="Panel") =>
            new JObject{["action"]=action,["expected_model_path"]=doc.Path,["component_id"]=id,["rhino_group_id"]=group.ToString("D"),
                ["name"]=name,["scene_ids"]=new JArray("inside"),["object_ids"]=new JArray((objects??new Guid[0]).Select(x=>x.ToString("D")))};
        private static JObject Success(JObject result)
        {Check((string)result["status"]=="success",result.ToString());return (JObject)result["component"];}
        private static void SuccessStatus(JObject result){Check((string)result["status"]=="success",result.ToString());}
        private static void Check(bool condition,string message){if(!condition)throw new InvalidOperationException(message);}
        private static void UndoRedo(RhinoDoc doc,bool redo)
        {
            Check(!doc.UndoRecordingIsActive,"Undo already active."); uint next=doc.NextUndoRecordSerialNumber;
            try{Check(redo?doc.Redo():doc.Undo(),"Undo/Redo failed.");}
            finally{if(doc.UndoRecordingIsActive&&doc.CurrentUndoRecordSerialNumber==next)Check(doc.EndUndoRecord(next),"Undo close failed.");}
        }
        private static void Run(List<string> results,string directory,string name,Action<RhinoDoc> test,bool legacyArchive=false)
        {
            string path=Path.Combine(directory,"semantic-"+Guid.NewGuid().ToString("N")+".3dm");
            if(legacyArchive)
            {
                using(var legacy=new Rhino.FileIO.File3dm()) Check(legacy.Write(path,8),"Legacy-format fixture save failed.");
            }
            else using(var original=RhinoDoc.CreateHeadless(null))
                Check(original.WriteFile(path,new Rhino.FileIO.FileWriteOptions{SuppressDialogBoxes=true}),"Fixture save failed.");
            using(var doc=RhinoDoc.OpenHeadless(path))
            {
                try{doc.UndoRecordingEnabled=true;test(doc);Check(!doc.UndoRecordingIsActive&&!doc.UndoActive&&!doc.RedoActive,"Leaked Undo state.");results.Add("PASS "+name);}
                catch(Exception error){results.Add("FAIL "+name+": "+error);}
                finally{if(doc!=null)doc.Modified=false;}
            }
        }
    }
}
