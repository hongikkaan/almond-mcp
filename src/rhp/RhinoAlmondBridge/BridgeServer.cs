using System;
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;

namespace RhinoAlmondBridge
{
    /// <summary>
    /// Native request handlers used by an authenticated, document-bound Engine session.
    /// Supported request types:
    ///   {"type": "execute", "script": "C# code..."}
    ///   {"type": "validate", "guids": [...], "structure_type": "beam", ...}
    ///   {"type": "run_definition", "capsule_id": "...", "manifest_path": "...", ...}
    ///   {"type": "export_glb", "guids": [...], "output_path": "..."}
    ///   {"type": "place_furniture", "asset_id": "...", "file_path": "...", ...}
    ///   {"type": "place_drawing_asset", "asset_id": "...", "file_path": "...", ...}
    ///   {"type": "import_hatch_patterns", "file_path": "..."}
    ///   {"type": "apply_drawing_style", "recipe_id": "...", "layers": [...]}
    /// The Engine owns transport, authentication, UI dispatch and completion tracking.
    /// </summary>
    public class BridgeServer : AlmondEngine.IBridgeRequestHandler
    {
        public IReadOnlyDictionary<string, string> LibraryDirectories { get; }
        private StructuralValidator _validator;
        private GhDefinitionRunner _definitionRunner;
        private FurnitureAssetManager _drawingAssetManager;
        private DrawingStyleManager _drawingStyleManager;

        public BridgeServer()
        {
            string libDir = ResolveLibraryDirectory("RHINO_MCP_LIBRARY_DIR", "Grasshopperfiles");
            string capsuleDir = ResolveLibraryDirectory("RHINO_MCP_CAPSULE_DIR", "capsules");
            _validator = new StructuralValidator(libDir, capsuleDir);
            _definitionRunner = new GhDefinitionRunner(libDir, capsuleDir);
            string drawingAssetDir = ResolveLibraryDirectory("RHINO_MCP_DRAWING_ASSET_DIR", "DrawingAssetfiles");
            _drawingAssetManager = new FurnitureAssetManager(
                drawingAssetDir,
                "ALMOND-DRAW::ASSETS",
                "DRAWING",
                "drawing_asset",
                "drawing asset",
                new[] { ".3dm", ".dwg", ".dxf", ".svg", ".png" }
            );
            _drawingStyleManager = new DrawingStyleManager();
            LibraryDirectories = new System.Collections.ObjectModel.ReadOnlyDictionary<string, string>(
                new Dictionary<string, string> {
                    ["RHINO_MCP_LIBRARY_DIR"] = libDir,
                    ["RHINO_MCP_CAPSULE_DIR"] = capsuleDir,
                    ["RHINO_MCP_DRAWING_ASSET_DIR"] = drawingAssetDir
                });
        }

        // Match runtime/library_paths.py, used by every real worker launcher.
        // Installing an editable checkout must not redirect personal libraries
        // into the source tree. Offline tests select checkout assets explicitly.
        internal static string ResolveLibraryDirectory(string variable, string name)
        {
            string selected = Environment.GetEnvironmentVariable(variable);
            if (!string.IsNullOrEmpty(selected)) return selected;
            return Path.Combine(
                Environment.GetEnvironmentVariable("LOCALAPPDATA")
                    ?? Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Almond", name
            );
        }

        /// <summary>
        /// Routes a JSON request to the appropriate handler based on the "type" field.
        /// </summary>
        public string HandleRequest(AlmondEngine.BridgeDispatchContext context, string json)
        {
            context.ValidateDocument();
            string response = Dispatch(context.Document, json);
            context.ValidateDocument();
            return response;
        }

        private string Dispatch(RhinoDoc doc, string json)
        {
            try
            {
                var jobj = JObject.Parse(json);
                string requestType = jobj.Value<string>("type") ?? "execute";

                switch (requestType.ToLower())
                {
                    case "get_rhino_context":
                        return DocumentObservation.HandleContext(doc, jobj);

                    case "get_rhino_viewport_image":
                        return DocumentObservation.HandleViewportImage(doc, jobj);

                    case "get_defined_viewcapture":
                    case "get_current_viewcapture":
                        return ViewCaptureTools.Handle(doc, jobj).ToString(Formatting.None);

                    case "manipulate_view":
                        return ViewManipulation.Handle(doc, jobj).ToString(Formatting.None);

                    case "get_rhino_objects":
                    case "get_object_intersections":
                        return ObjectObservation.Handle(doc, jobj).ToString(Formatting.None);

                    case "capture_rhino_inspection":
                        return InspectionCapture.Handle(doc, jobj).ToString(Formatting.None);

                    case "edit_planar_face":
                        return PlanarFaceEditing.Handle(doc, jobj).ToString(Formatting.None);

                    case "edit_planar_faces":
                        return PlanarFaceEditing.HandleBatch(doc, jobj).ToString(Formatting.None);

                    case "plan_section":
                        return PlanSectionTool.Handle(doc, jobj).ToString(Formatting.None);

                    case "cleanup_step_temp":
                        return StepTempCleanup.Handle(doc, jobj).ToString(Formatting.None);

                    case "intersection_preview":
                        return IntersectionTools.PreviewHandle(doc, jobj).ToString(Formatting.None);

                    case "intersection_review":
                        return IntersectionReview.Capture(doc, jobj).ToString(Formatting.None);

                    case "intersection_resolve":
                        return IntersectionTools.ResolveHandle(doc, jobj).ToString(Formatting.None);

                    case "save_rhino_document":
                        return DocumentSave.Handle(doc, jobj).ToString(Formatting.None);

                    case "analyze_block_reculviely":
                        return BlockAnalysis.Analyze(doc, jobj).ToString(Formatting.None);

                    case "design_component":
                        return ComponentRegistry.Handle(doc, jobj).ToString(Formatting.None);

                    case "drawing_sheet":
                        return JsonConvert.SerializeObject(new { status = "error", error_code = "retired_tool",
                            message = "Sheet database registration has been removed. Existing Layouts are unchanged." });

                    case "component_operation":
                        return ComponentOperations.Handle(doc, jobj).ToString(Formatting.None);

                    case "drawing_asset_extract":
                        return DrawingAssetGeometry.Handle(jobj).ToString(Formatting.None);

                    case "place_drawing_asset":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Placing indexed drawing asset...");
                        var drawingAssetRequest = jobj.ToObject<FurniturePlacementRequest>();
                        var drawingAssetResult = _drawingAssetManager.Place(doc, drawingAssetRequest);
                        return JsonConvert.SerializeObject(drawingAssetResult);

                    case "import_hatch_patterns":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Importing hatch patterns...");
                        string hatchFilePath = jobj.Value<string>("file_path") ?? "";
                        var hatchResult = _drawingAssetManager.ImportHatchPatterns(doc, hatchFilePath);
                        return JsonConvert.SerializeObject(hatchResult);

                    case "apply_drawing_style":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Applying drawing layer style...");
                        var drawingStyleRequest = jobj.ToObject<DrawingStyleRequest>();
                        var drawingStyleResult = _drawingStyleManager.Apply(doc, drawingStyleRequest);
                        return JsonConvert.SerializeObject(drawingStyleResult);

                    case "export_glb":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Exporting linked GLB...");
                        var exportRequest = jobj.ToObject<GlbExportRequest>();
                        var exportResult = new GlbExporter().Export(doc, exportRequest);
                        return JsonConvert.SerializeObject(exportResult);

                    case "run_definition":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Running capsule definition...");
                        return HandleRunDefinition(doc, jobj);

                    case "validate":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Running structural validation...");
                        var valRequest = jobj.ToObject<ValidationRequest>();
                        var valResult = _validator.Validate(doc, valRequest);
                        RhinoApp.WriteLine($"RhinoAlmondBridge: Validation {valResult.Status}: {valResult.Verdict}");
                        return JsonConvert.SerializeObject(valResult);

                    case "structure_model":
                        return StructureModelExport.Handle(doc, jobj);

                    case "structure_draw":
                        return StructureView.HandleDraw(doc, jobj);

                    case "asset_placements":
                        return AssetPlacementExport.Handle(doc, jobj);

                    case "structure_view":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Structure view (Karamba live)...");
                        return StructureView.Handle(doc, jobj);

                    case "execute":
                        string script = jobj.Value<string>("script") ?? "";
                        var executor = new ScriptExecutor();
                        using (ManagedFiles.Bind(doc, jobj.Value<string>("project_root"), jobj.Value<string>("artifact_dir")))
                            return JsonConvert.SerializeObject(executor.Execute(script, doc));

                    default:
                        return JsonConvert.SerializeObject(new { status = "error", error_code = "unsupported_request",
                            message = "Unsupported bridge request type: " + requestType });
                }
            }
            catch (Exception ex)
            {
                var error = new { status = "error", message = ex.Message, error_trace = ex.ToString() };
                return JsonConvert.SerializeObject(error);
            }
        }

        /// <summary>
        /// Handles {"type": "run_definition", "capsule_id": "...",
        ///          "manifest_path": "...", "inputs": {...},
        ///          "seed": 42, "timeout_s": 60}
        /// and answers with the existing payload contract:
        /// {"status": "ok|error", "capsule_id": "...", "outputs": {...},
        ///  "baked_guids": [], "analysis_method": "api|template|rule_based",
        ///  "confidence": "high|medium|low", "warnings": [], "error": null}
        /// </summary>
        private string HandleRunDefinition(RhinoDoc doc, JObject jobj)
        {
            string capsuleId = jobj.Value<string>("capsule_id");
            string manifestPath = jobj.Value<string>("manifest_path");
            var inputs = jobj["inputs"] as JObject;
            int? seed = jobj.Value<int?>("seed");
            double timeoutS = jobj.Value<double?>("timeout_s") ?? 60.0;

            string Respond(string status, string cid, Dictionary<string, object> outputs,
                List<string> bakedGuids, string method, string confidence,
                List<string> warnings, string error, string mutationState = "none", bool requiresReconciliation = false)
            {
                return JsonConvert.SerializeObject(new
                {
                    status = status,
                    capsule_id = cid,
                    outputs = outputs ?? new Dictionary<string, object>(),
                    baked_guids = bakedGuids ?? new List<string>(),
                    analysis_method = method,
                    confidence = confidence,
                    warnings = warnings ?? new List<string>(),
                    error = error,
                    mutation_state = mutationState,
                    requires_reconciliation = requiresReconciliation,
                });
            }

            // Resolve the manifest: explicit path wins, else look up by capsule_id.
            if (string.IsNullOrEmpty(manifestPath) && !string.IsNullOrEmpty(capsuleId))
                manifestPath = _definitionRunner.FindManifestPath(capsuleId);

            if (string.IsNullOrEmpty(manifestPath))
            {
                return Respond("error", capsuleId, null, null, "template", "medium", null,
                    $"No manifest found for capsule_id '{capsuleId}' and no manifest_path given.");
            }

            // Manifest confidence drives the reported method/confidence pair:
            // api → high, template → medium, rule_based → low.
            string loadError;
            var manifest = GhDefinitionRunner.LoadManifest(manifestPath, out loadError);
            string analysisMethod = manifest?.Confidence ?? "template";
            string confidenceLevel =
                analysisMethod == "api" ? "high" :
                analysisMethod == "rule_based" ? "low" : "medium";

            if (manifest == null)
            {
                return Respond("error", capsuleId, null, null, analysisMethod,
                    confidenceLevel, null, loadError);
            }

            var runResult = _definitionRunner.Run(doc, manifestPath, inputs, timeoutS, seed);

            return Respond(
                runResult.Status == "ok" ? "ok" : "error",
                runResult.CapsuleId ?? manifest.CapsuleId ?? capsuleId,
                runResult.Outputs,
                runResult.BakedGuids,
                analysisMethod,
                confidenceLevel,
                runResult.Warnings,
                runResult.Error, runResult.MutationState, runResult.RequiresReconciliation);
        }

    }
}
