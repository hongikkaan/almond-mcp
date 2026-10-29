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
    public class BridgeServer
    {
        private StructuralValidator _validator;
        private GhDefinitionRunner _definitionRunner;
        private FurnitureAssetManager _drawingAssetManager;
        private DrawingStyleManager _drawingStyleManager;

        public BridgeServer()
        {
            // Resolve the Grasshopper library directory from environment or default
            string libDir = Environment.GetEnvironmentVariable("RHINO_MCP_LIBRARY_DIR")
                ?? FindLibraryDirectory();
            string capsuleDir = Environment.GetEnvironmentVariable("RHINO_MCP_CAPSULE_DIR")
                ?? FindCapsuleDirectory();
            _validator = new StructuralValidator(libDir, capsuleDir);
            _definitionRunner = new GhDefinitionRunner(libDir, capsuleDir);
            string drawingAssetDir = Environment.GetEnvironmentVariable("RHINO_MCP_DRAWING_ASSET_DIR")
                ?? FindDrawingAssetDirectory();
            _drawingAssetManager = new FurnitureAssetManager(
                drawingAssetDir,
                "ALMOND-DRAW::ASSETS",
                "DRAWING",
                "drawing_asset",
                "drawing asset",
                new[] { ".skp", ".3dm", ".dwg", ".dxf", ".svg", ".png" }
            );
            _drawingStyleManager = new DrawingStyleManager();
        }

        // Resolve a library dir the same way the Python server does:
        // env var (handled by callers) -> dev checkout near the assembly ->
        // per-user data dir (%LOCALAPPDATA%\Almond\<name>, scaffolded by
        // `almond-mcp` on first run) -> legacy pre-0.2 location.
        private string FindDataDirectory(string name, string legacySubdir)
        {
            string assetPath = name == "capsules" ? Path.Combine("asset", "capsules")
                : name == "DrawingAssetfiles" ? Path.Combine("asset", "drawing", "DrawingAssetfiles")
                : name == "Grasshopperfiles" ? Path.Combine("asset", "grasshopper", "Grasshopperfiles") : null;
            string directory = Path.GetDirectoryName(typeof(BridgeServer).Assembly.Location);
            // Include the checkout root from src/rhp/<project>/bin/Release/<tfm>.
            for (int i = 0; i < 7 && directory != null; i++)
            {
                if (assetPath != null)
                {
                    string assetCandidate = Path.Combine(directory, assetPath);
                    if (Directory.Exists(assetCandidate)) return assetCandidate;
                }
                string candidate = Path.Combine(directory, name);
                if (Directory.Exists(candidate)) return candidate;
                directory = Path.GetDirectoryName(directory);
            }

            string userData = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Almond",
                name
            );
            if (Directory.Exists(userData)) return userData;

            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                "Almond",
                legacySubdir,
                name
            );
        }

        private string FindLibraryDirectory() => FindDataDirectory("Grasshopperfiles", "");


        private string FindCapsuleDirectory() => FindDataDirectory("capsules", "mcp-rhino-plugin");

        private string FindDrawingAssetDirectory() => FindDataDirectory("DrawingAssetfiles", "mcp-rhino-plugin");

        /// <summary>
        /// Routes a JSON request to the appropriate handler based on the "type" field.
        /// </summary>
        private string HandleRequest(string json)
        {
            try
            {
                var jobj = JObject.Parse(json);
                string requestType = jobj.Value<string>("type") ?? "execute";

                switch (requestType.ToLower())
                {
                    case "get_rhino_context":
                        return DocumentObservation.HandleContext(jobj);

                    case "get_rhino_viewport_image":
                        return DocumentObservation.HandleViewportImage(jobj);

                    case "save_rhino_document":
                        return DocumentSave.Handle(RhinoDoc.ActiveDoc, jobj).ToString(Formatting.None);

                    case "analyze_block_reculviely":
                        return BlockAnalysis.Handle(jobj);

                    case "design_component":
                        return ComponentRegistry.Handle(RhinoDoc.ActiveDoc, jobj).ToString(Formatting.None);

                    case "drawing_sheet":
                        return JsonConvert.SerializeObject(new { status = "error", error_code = "retired_tool",
                            message = "Sheet database registration has been removed. Existing Layouts are unchanged." });

                    case "component_operation":
                        return ComponentOperations.Handle(RhinoDoc.ActiveDoc, jobj).ToString(Formatting.None);

                    case "drawing_asset_extract":
                        return DrawingAssetGeometry.Handle(jobj).ToString(Formatting.None);

                    case "place_drawing_asset":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Placing indexed drawing asset...");
                        var drawingAssetRequest = jobj.ToObject<FurniturePlacementRequest>();
                        var drawingAssetResult = _drawingAssetManager.Place(drawingAssetRequest);
                        return JsonConvert.SerializeObject(drawingAssetResult);

                    case "import_hatch_patterns":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Importing hatch patterns...");
                        string hatchFilePath = jobj.Value<string>("file_path") ?? "";
                        var hatchResult = _drawingAssetManager.ImportHatchPatterns(hatchFilePath);
                        return JsonConvert.SerializeObject(hatchResult);

                    case "apply_drawing_style":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Applying drawing layer style...");
                        var drawingStyleRequest = jobj.ToObject<DrawingStyleRequest>();
                        var drawingStyleResult = _drawingStyleManager.Apply(drawingStyleRequest);
                        return JsonConvert.SerializeObject(drawingStyleResult);

                    case "export_glb":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Exporting linked GLB...");
                        var exportRequest = jobj.ToObject<GlbExportRequest>();
                        var exportResult = new GlbExporter().Export(exportRequest);
                        return JsonConvert.SerializeObject(exportResult);

                    case "run_definition":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Running capsule definition...");
                        return HandleRunDefinition(jobj);

                    case "validate":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Running structural validation...");
                        var valRequest = jobj.ToObject<ValidationRequest>();
                        var valResult = _validator.Validate(valRequest);
                        RhinoApp.WriteLine($"RhinoAlmondBridge: Validation {valResult.Status}: {valResult.Verdict}");
                        return JsonConvert.SerializeObject(valResult);

                    case "structure_model":
                        return StructureModelExport.Handle(jobj);

                    case "structure_draw":
                        return StructureView.HandleDraw(jobj);

                    case "asset_placements":
                        return AssetPlacementExport.Handle(jobj);

                    case "structure_view":
                        RhinoApp.WriteLine("RhinoAlmondBridge: Structure view (Karamba live)...");
                        return StructureView.Handle(jobj);

                    case "execute":
                        string script = jobj.Value<string>("script") ?? "";
                        var executor = new ScriptExecutor();
                        using (ManagedFiles.Bind(RhinoDoc.ActiveDoc, jobj.Value<string>("project_root"), jobj.Value<string>("artifact_dir")))
                            return JsonConvert.SerializeObject(executor.Execute(script));

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
        private string HandleRunDefinition(JObject jobj)
        {
            string capsuleId = jobj.Value<string>("capsule_id");
            string manifestPath = jobj.Value<string>("manifest_path");
            var inputs = jobj["inputs"] as JObject;
            int? seed = jobj.Value<int?>("seed");
            double timeoutS = jobj.Value<double?>("timeout_s") ?? 60.0;

            string Respond(string status, string cid, Dictionary<string, object> outputs,
                List<string> bakedGuids, string method, string confidence,
                List<string> warnings, string error)
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

            var runResult = _definitionRunner.Run(manifestPath, inputs, timeoutS, seed);

            return Respond(
                runResult.Status == "ok" ? "ok" : "error",
                runResult.CapsuleId ?? manifest.CapsuleId ?? capsuleId,
                runResult.Outputs,
                runResult.BakedGuids,
                analysisMethod,
                confidenceLevel,
                runResult.Warnings,
                runResult.Error);
        }

    }
}
