using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Rhino;
using Rhino.DocObjects;
using Rhino.FileIO;
using Rhino.Geometry;

namespace RhinoAlmondBridge
{
    public class FurnitureAssetManager
    {
        private readonly string _libraryRoot;
        private readonly string _layerPath;
        private readonly string _blockPrefix;
        private readonly string _assetType;
        private readonly string _displayName;
        private readonly HashSet<string> _allowedExtensions;

        private static readonly HashSet<string> RasterExtensions =
            new HashSet<string>(StringComparer.OrdinalIgnoreCase) { ".png" };

        public FurnitureAssetManager(
            string libraryRoot,
            string layerPath = "ALMOND-ASSETS",
            string blockPrefix = "ALMOND",
            string assetType = "library_asset",
            string displayName = "furniture",
            IEnumerable<string> allowedExtensions = null)
        {
            _libraryRoot = Path.GetFullPath(libraryRoot ?? "");
            _layerPath = layerPath;
            _blockPrefix = blockPrefix;
            _assetType = assetType;
            _displayName = displayName;
            _allowedExtensions = new HashSet<string>(
                allowedExtensions ?? new[] { ".skp" },
                StringComparer.OrdinalIgnoreCase
            );
        }

        public FurniturePlacementResult Place(FurniturePlacementRequest request) =>
            PlaceCore(RhinoDoc.ActiveDoc, request, false);

        // The native panel command owns its command Undo record. This is deliberately
        // not a request field: MCP callers cannot opt out of the fixed mutation guard.
        internal FurniturePlacementResult PlaceInCommand(RhinoDoc doc, FurniturePlacementRequest request) =>
            PlaceCore(doc, request, true);

        private FurniturePlacementResult PlaceCore(RhinoDoc doc, FurniturePlacementRequest request, bool commandUndo)
        {
            var result = new FurniturePlacementResult
            {
                Status = "error",
                AssetId = request?.AssetId
            };

            if (request == null)
            {
                result.Message = $"{_displayName} request is required.";
                return result;
            }

            string validationError;
            string fullPath = ValidateAssetPath(request.FilePath, out validationError);
            if (fullPath == null)
            {
                result.Message = validationError;
                return result;
            }

            if (doc == null)
            {
                result.Message = "No active Rhino document.";
                return result;
            }

            uint undoRecord = 0;
            bool mutationStarted = false;
            try
            {
                if (doc.IsReadOnly || (!commandUndo && doc.UndoRecordingIsActive) || doc.UndoActive || doc.RedoActive)
                    throw new InvalidOperationException("Finish the current edit or Undo/Redo before placing an asset in an editable document.");
                if (commandUndo && (doc.InCommand(false) == 0 || RhinoDoc.ActiveDoc?.RuntimeSerialNumber != doc.RuntimeSerialNumber))
                    throw new InvalidOperationException("Panel placement requires its active Rhino command and document.");
                Point3d position = ReadPosition(request.Position);
                if (!Double.IsFinite(request.Scale) || request.Scale <= 0 || !Double.IsFinite(request.RotationDegrees))
                    throw new ArgumentException("Placement scale must be finite and positive; rotation must be finite.");
                string definitionName = BuildDefinitionName(request.AssetId);
                bool linkedModel = String.Equals(Path.GetExtension(fullPath), ".3dm", StringComparison.OrdinalIgnoreCase);
                string sourceHash = null;
                UnitSystem sourceUnits = doc.ModelUnitSystem;
                if (linkedModel)
                {
                    if (doc.ModelUnitSystem == UnitSystem.None || doc.ModelUnitSystem == UnitSystem.CustomUnits)
                        throw new ArgumentException("Set standard model units before placing a 3DM drawing asset.");
                    if (String.IsNullOrWhiteSpace(request.AssetId))
                        throw new ArgumentException("A registered asset ID is required for linked 3DM placement.");
                    sourceHash = FileHash(fullPath);
                    string expected = (string)request.Metadata?["sha256"];
                    if (!String.Equals(expected, sourceHash, StringComparison.OrdinalIgnoreCase))
                    {
                        result.ErrorCode = "asset_needs_refresh";
                        result.NeedsRefresh = true;
                        result.Message = "The 3DM differs from its registered measurements. Call refresh_asset(asset_id) before placement.";
                        return result;
                    }
                    using (var source = File3dm.Read(fullPath))
                    {
                        if (source == null) throw new InvalidDataException("Rhino could not read the source 3DM.");
                        DrawingAssetGeometry.RequireSelfContainedDefinitions(source);
                        sourceUnits = source.Settings.ModelUnitSystem;
                    }
                    if (sourceUnits == UnitSystem.None || sourceUnits == UnitSystem.CustomUnits)
                        throw new ArgumentException("The source 3DM needs standard model units.");
                    definitionName += "::LINK::" + PathIdentity(fullPath) + "::" + doc.ModelUnitSystem;
                }
                var definition = FindDefinition(doc, definitionName);
                if (linkedModel && definition != null)
                    RequireLinkedDefinition(definition, fullPath, sourceUnits);
                if (!commandUndo)
                {
                    undoRecord = doc.BeginUndoRecord($"Place {_displayName}");
                    if (undoRecord == 0)
                        throw new InvalidOperationException("Rhino could not begin the asset-placement Undo record; nothing was placed.");
                }
                mutationStarted = true;
                bool definitionCreated = false;

                if (definition == null)
                {
                    definition = linkedModel
                        ? BuildLinkedDefinition(doc, fullPath, definitionName, request.Name, sourceUnits)
                        : RasterExtensions.Contains(Path.GetExtension(fullPath))
                        ? BuildRasterDefinition(doc, fullPath, definitionName, request.Name, request.Metadata)
                        : ImportAsDefinition(doc, fullPath, definitionName, request.Name);
                    definitionCreated = true;
                }
                else if (linkedModel && definition.ArchiveFileStatus != InstanceDefinitionArchiveFileStatus.LinkedFileIsUpToDate)
                {
                    result.AffectedExistingInstances = definition.GetReferences(1).Length;
                    if (!doc.InstanceDefinitions.UpdateLinkedInstanceDefinition(definition.Index, fullPath, true, true))
                        throw new InvalidOperationException("Rhino could not refresh the linked asset definition.");
                    definition = doc.InstanceDefinitions[definition.Index];
                    RequireLinkedDefinition(definition, fullPath, sourceUnits);
                    result.DefinitionRefreshed = true;
                }
                double unitScale = 1.0;
                if (linkedModel)
                {
                    RequireLinkedDefinition(definition, fullPath, sourceUnits);
                    if (!String.Equals(sourceHash, FileHash(fullPath), StringComparison.OrdinalIgnoreCase))
                        throw new IOException("The source 3DM changed during linked placement; inspect the definition before retrying.");
                    unitScale = RhinoMath.UnitScale(definition.UnitSystem, doc.ModelUnitSystem);
                    if (!Double.IsFinite(unitScale) || unitScale <= 0)
                        throw new InvalidOperationException("The linked definition has an invalid unit conversion.");
                }

                double angleRadians = RhinoMath.ToRadians(request.RotationDegrees);
                Transform transform =
                    Transform.Translation(position.X, position.Y, position.Z) *
                    Transform.Rotation(angleRadians, Vector3d.ZAxis, Point3d.Origin) *
                    Transform.Scale(Point3d.Origin, request.Scale * unitScale);

                var attributes = BuildInstanceAttributes(doc, request);
                if (linkedModel)
                {
                    attributes.SetUserString("almond.asset_source", fullPath);
                    attributes.SetUserString("almond.metadata_scope", "source_at_placement");
                }
                Guid objectId = doc.Objects.AddInstanceObject(definition.Index, transform, attributes);
                if (objectId == Guid.Empty)
                    throw new InvalidOperationException($"Rhino failed to create the {_displayName} block instance.");

                doc.Views.Redraw();
                var placedObject = doc.Objects.FindId(objectId);
                BoundingBox bounds = placedObject?.Geometry?.GetBoundingBox(true) ?? BoundingBox.Empty;

                result.Status = "success";
                result.Message = definitionCreated
                    ? $"{_displayName} imported and placed as a new block definition."
                    : $"{_displayName} placed using the existing block definition.";
                result.ObjectGuid = objectId.ToString();
                result.BlockDefinition = definition.Name;
                result.DefinitionCreated = definitionCreated;
                result.Bounds = BoundsPayload.FromBoundingBox(bounds);
                if (linkedModel)
                {
                    result.LinkType = "linked";
                    result.LayerStyle = "active";
                    result.SourcePath = fullPath;
                    result.SourceSha256 = sourceHash;
                    result.MetadataScope = "source_at_placement";
                }
                result.MutationState = "completed";
                return result;
            }
            catch (Exception ex)
            {
                result.Message = ex.Message;
                result.ErrorTrace = ex.ToString();
                if (ex is DrawingAssetGeometry.AssetDependencyException)
                    result.ErrorCode = "asset_dependencies_unverified";
                result.MutationState = mutationStarted ? "unknown" : "not_started";
                result.RequiresReconciliation = mutationStarted;
                return result;
            }
            finally
            {
                if (undoRecord != 0)
                    doc.EndUndoRecord(undoRecord);
            }
        }

        private static string FileHash(string path)
        {
            using (var stream = File.OpenRead(path))
            using (var algorithm = SHA256.Create())
                return BitConverter.ToString(algorithm.ComputeHash(stream)).Replace("-", "");
        }

        private static string PathIdentity(string path)
        {
            using (var algorithm = SHA256.Create())
                return BitConverter.ToString(algorithm.ComputeHash(Encoding.UTF8.GetBytes(Path.GetFullPath(path).ToUpperInvariant())))
                    .Replace("-", "").Substring(0, 16);
        }

        private static void RequireLinkedDefinition(InstanceDefinition definition, string source, UnitSystem sourceUnits)
        {
            if (definition.UpdateType != InstanceDefinitionUpdateType.Linked ||
                definition.LayerStyle != InstanceDefinitionLayerStyle.Active ||
                String.IsNullOrWhiteSpace(definition.SourceArchive) ||
                !String.Equals(Path.GetFullPath(definition.SourceArchive), Path.GetFullPath(source), StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("The asset definition name belongs to a different or embedded block; it was not reused or changed.");
            if (definition.UnitSystem != sourceUnits)
                throw new InvalidOperationException("The linked source unit system changed. Reconcile existing instance scales before reusing this definition.");
        }

        private static InstanceDefinition BuildLinkedDefinition(RhinoDoc doc, string filePath,
            string definitionName, string description, UnitSystem sourceUnits)
        {
            // Rhino 8 has no AddFromFile. A definition-local seed enables its supported
            // source/archive loader without importing temporary objects into model space.
            int index;
            using (var seed = new Rhino.Geometry.Point(Point3d.Origin))
                index = doc.InstanceDefinitions.Add(definitionName, description ?? "Linked model asset",
                    Point3d.Origin, seed, new ObjectAttributes());
            if (index < 0) throw new InvalidOperationException("Rhino could not create the linked asset definition.");
            try
            {
                var definition = doc.InstanceDefinitions[index];
                definition.UnitSystem = sourceUnits;
                using (var reference = FileReference.CreateFromFullPath(filePath))
                    if (!doc.InstanceDefinitions.ModifySourceArchive(index, reference, InstanceDefinitionUpdateType.Linked, true))
                        throw new InvalidOperationException("Rhino could not link the asset source 3DM.");
                definition = doc.InstanceDefinitions[index];
                definition.LayerStyle = InstanceDefinitionLayerStyle.Active;
                if (!doc.InstanceDefinitions.UpdateLinkedInstanceDefinition(index, filePath, true, true))
                    throw new InvalidOperationException("Rhino could not read the linked asset source 3DM.");
                definition = doc.InstanceDefinitions[index];
                RequireLinkedDefinition(definition, filePath, sourceUnits);
                if (definition.ObjectCount == 0)
                    throw new InvalidOperationException("The linked asset source contains no definition geometry.");
                return definition;
            }
            catch
            {
                // Only our new, unreferenced definition is eligible for cleanup.
                doc.InstanceDefinitions.Delete(index, false, true);
                throw;
            }
        }

        private string ValidateAssetPath(string filePath, out string error)
        {
            error = null;
            if (string.IsNullOrWhiteSpace(filePath))
            {
                error = $"{_displayName} file path is required.";
                return null;
            }

            string fullPath = Path.GetFullPath(filePath);
            string rootWithSeparator = _libraryRoot.TrimEnd(
                Path.DirectorySeparatorChar,
                Path.AltDirectorySeparatorChar
            ) + Path.DirectorySeparatorChar;

            if (!fullPath.StartsWith(rootWithSeparator, StringComparison.OrdinalIgnoreCase))
            {
                error = $"{_displayName} file is outside its configured library.";
                return null;
            }
            if (!_allowedExtensions.Contains(Path.GetExtension(fullPath)))
            {
                error = $"Only indexed {_displayName} files with extensions " +
                    $"{string.Join(", ", _allowedExtensions.OrderBy(e => e))} are supported.";
                return null;
            }
            if (!File.Exists(fullPath))
            {
                error = $"{_displayName} file does not exist.";
                return null;
            }
            return fullPath;
        }

        private InstanceDefinition ImportAsDefinition(
            RhinoDoc doc,
            string filePath,
            string definitionName,
            string description)
        {
            string extension = Path.GetExtension(filePath);
            var beforeIds = new HashSet<Guid>(doc.Objects.Select(obj => obj.Id));
            string escapedPath = filePath.Replace("\"", "\"\"");
            bool imported = RhinoApp.RunScript($"_-Import \"{escapedPath}\" _Enter", false);
            if (!imported)
                throw new InvalidOperationException($"Rhino's {extension} importer did not complete.");

            var importedObjects = doc.Objects
                .Where(obj => !beforeIds.Contains(obj.Id) && !obj.IsDeleted)
                .ToList();
            if (importedObjects.Count == 0)
                throw new InvalidOperationException($"{extension} import created no Rhino objects.");

            try
            {
                var geometry = new List<GeometryBase>();
                var attributes = new List<ObjectAttributes>();
                BoundingBox bounds = BoundingBox.Empty;
                bool hasBounds = false;

                foreach (var importedObject in importedObjects)
                {
                    GeometryBase duplicate = importedObject.Geometry?.Duplicate();
                    if (duplicate == null)
                        continue;
                    geometry.Add(duplicate);
                    attributes.Add(importedObject.Attributes.Duplicate());

                    BoundingBox objectBounds = duplicate.GetBoundingBox(true);
                    if (objectBounds.IsValid)
                    {
                        if (!hasBounds)
                        {
                            bounds = objectBounds;
                            hasBounds = true;
                        }
                        else
                        {
                            bounds.Union(objectBounds);
                        }
                    }
                }

                if (geometry.Count == 0 || !hasBounds)
                    throw new InvalidOperationException($"Imported {extension} file contained no usable geometry.");

                var basePoint = new Point3d(bounds.Center.X, bounds.Center.Y, bounds.Min.Z);
                int definitionIndex = doc.InstanceDefinitions.Add(
                    definitionName,
                    description ?? $"Indexed {_displayName}",
                    basePoint,
                    geometry,
                    attributes
                );
                if (definitionIndex < 0)
                    throw new InvalidOperationException($"Rhino failed to create the {_displayName} block definition.");

                return doc.InstanceDefinitions[definitionIndex];
            }
            finally
            {
                foreach (var importedObject in importedObjects)
                    doc.Objects.Delete(importedObject.Id, true);
            }
        }

        /// <summary>
        /// Builds a block definition for a transparent raster asset (for
        /// example a PNG entourage cut-out): an upright textured quad with
        /// alpha transparency, bottom-centre anchored at the origin. Physical
        /// size comes from manifest dimensions_mm when present, otherwise from
        /// pixel dimensions at 96 dpi.
        /// </summary>
        private InstanceDefinition BuildRasterDefinition(
            RhinoDoc doc,
            string filePath,
            string definitionName,
            string description,
            JObject metadata)
        {
            double widthMm = 0.0;
            double heightMm = 0.0;
            var dimensions = metadata?["dimensions_mm"] as JObject;
            if (dimensions != null)
            {
                widthMm = dimensions.Value<double?>("width") ?? 0.0;
                heightMm = dimensions.Value<double?>("height") ?? 0.0;
            }

            int pixelWidth;
            int pixelHeight;
            using (var bitmap = new System.Drawing.Bitmap(filePath))
            {
                pixelWidth = bitmap.Width;
                pixelHeight = bitmap.Height;
            }
            if (pixelWidth <= 0 || pixelHeight <= 0)
                throw new InvalidOperationException("Raster asset has invalid pixel dimensions.");

            if (widthMm <= 0.0 && heightMm <= 0.0)
                widthMm = pixelWidth * 25.4 / 96.0;
            if (widthMm <= 0.0)
                widthMm = heightMm * pixelWidth / pixelHeight;
            if (heightMm <= 0.0)
                heightMm = widthMm * pixelHeight / pixelWidth;

            var mesh = new Mesh();
            mesh.Vertices.Add(-widthMm / 2.0, 0.0, 0.0);
            mesh.Vertices.Add(widthMm / 2.0, 0.0, 0.0);
            mesh.Vertices.Add(widthMm / 2.0, 0.0, heightMm);
            mesh.Vertices.Add(-widthMm / 2.0, 0.0, heightMm);
            mesh.TextureCoordinates.Add(0.0, 0.0);
            mesh.TextureCoordinates.Add(1.0, 0.0);
            mesh.TextureCoordinates.Add(1.0, 1.0);
            mesh.TextureCoordinates.Add(0.0, 1.0);
            mesh.Faces.AddFace(0, 1, 2, 3);
            mesh.Normals.ComputeNormals();
            mesh.Compact();

            int materialIndex = doc.Materials.Add();
            if (materialIndex < 0)
                throw new InvalidOperationException("Rhino failed to create the raster material.");
            var material = doc.Materials[materialIndex];
            material.Name = definitionName;
            material.SetBitmapTexture(filePath);
            material.AlphaTransparency = true;
            material.CommitChanges();

            var attributes = new ObjectAttributes
            {
                MaterialIndex = materialIndex,
                MaterialSource = ObjectMaterialSource.MaterialFromObject
            };

            int definitionIndex = doc.InstanceDefinitions.Add(
                definitionName,
                description ?? $"Indexed raster {_displayName}",
                Point3d.Origin,
                new GeometryBase[] { mesh },
                new[] { attributes }
            );
            if (definitionIndex < 0)
                throw new InvalidOperationException($"Rhino failed to create the raster {_displayName} block definition.");

            return doc.InstanceDefinitions[definitionIndex];
        }

        /// <summary>
        /// Imports AutoCAD-style .pat hatch definitions from the controlled
        /// library root into the active document's hatch pattern table.
        /// </summary>
        public HatchPatternImportResult ImportHatchPatterns(string filePath)
        {
            var result = new HatchPatternImportResult
            {
                Status = "error",
                Patterns = new List<string>()
            };

            if (string.IsNullOrWhiteSpace(filePath))
            {
                result.Message = "Hatch pattern file path is required.";
                return result;
            }
            string fullPath = Path.GetFullPath(filePath);
            string rootWithSeparator = _libraryRoot.TrimEnd(
                Path.DirectorySeparatorChar,
                Path.AltDirectorySeparatorChar
            ) + Path.DirectorySeparatorChar;
            if (!fullPath.StartsWith(rootWithSeparator, StringComparison.OrdinalIgnoreCase))
            {
                result.Message = "Hatch pattern file is outside its configured library.";
                return result;
            }
            if (!string.Equals(Path.GetExtension(fullPath), ".pat", StringComparison.OrdinalIgnoreCase))
            {
                result.Message = "Only .pat hatch definition files are supported.";
                return result;
            }
            if (!File.Exists(fullPath))
            {
                result.Message = "Hatch pattern file does not exist.";
                return result;
            }

            var doc = RhinoDoc.ActiveDoc;
            if (doc == null)
            {
                result.Message = "No active Rhino document.";
                return result;
            }

            try
            {
                HatchPattern[] patterns = HatchPattern.ReadFromFile(fullPath, true);
                if (patterns == null || patterns.Length == 0)
                {
                    result.Message = "No hatch patterns were found in the file.";
                    return result;
                }
                int added = 0;
                foreach (var pattern in patterns)
                {
                    if (pattern == null || string.IsNullOrWhiteSpace(pattern.Name))
                        continue;
                    if (doc.HatchPatterns.FindName(pattern.Name) == null)
                    {
                        if (doc.HatchPatterns.Add(pattern) < 0)
                            continue;
                        added++;
                    }
                    result.Patterns.Add(pattern.Name);
                }
                result.Status = "success";
                result.Message = $"Imported {added} new hatch patterns ({result.Patterns.Count} available).";
                return result;
            }
            catch (Exception ex)
            {
                result.Message = ex.Message;
                result.ErrorTrace = ex.ToString();
                return result;
            }
        }

        private static InstanceDefinition FindDefinition(RhinoDoc doc, string name)
        {
            foreach (var definition in doc.InstanceDefinitions)
            {
                if (definition != null &&
                    !definition.IsDeleted &&
                    string.Equals(definition.Name, name, StringComparison.OrdinalIgnoreCase))
                    return definition;
            }
            return null;
        }

        private ObjectAttributes BuildInstanceAttributes(
            RhinoDoc doc,
            FurniturePlacementRequest request)
        {
            int layerIndex = DocumentLayers.Ensure(doc, _layerPath);
            var attributes = new ObjectAttributes
            {
                Name = request.Name ?? request.AssetId,
                LayerIndex = layerIndex
            };
            attributes.SetUserString("almond.asset_id", request.AssetId ?? "");
            attributes.SetUserString("almond.asset_type", _assetType);
            attributes.SetUserString("almond.metadata", request.Metadata?.ToString(Formatting.None) ?? "{}");
            return attributes;
        }

        private static Point3d ReadPosition(double[] position)
        {
            if (position == null || position.Length != 3)
                throw new ArgumentException("position must contain exactly three coordinates.");
            if (position.Any(value => double.IsNaN(value) || double.IsInfinity(value)))
                throw new ArgumentException("position coordinates must be finite.");
            return new Point3d(position[0], position[1], position[2]);
        }

        private string BuildDefinitionName(string assetId)
        {
            string safeId = Regex.Replace(assetId ?? "unknown", @"[^A-Za-z0-9._-]+", "-");
            return $"{_blockPrefix}::{safeId}";
        }
    }

    public class HatchPatternImportResult
    {
        [JsonProperty("status")]
        public string Status { get; set; }

        [JsonProperty("message")]
        public string Message { get; set; }

        [JsonProperty("patterns")]
        public List<string> Patterns { get; set; }

        [JsonProperty("error_trace")]
        public string ErrorTrace { get; set; }
    }

    public class FurniturePlacementRequest
    {
        [JsonProperty("asset_id")]
        public string AssetId { get; set; }

        [JsonProperty("file_path")]
        public string FilePath { get; set; }

        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("position")]
        public double[] Position { get; set; }

        [JsonProperty("rotation_degrees")]
        public double RotationDegrees { get; set; }

        [JsonProperty("scale")]
        public double Scale { get; set; } = 1.0;

        [JsonProperty("metadata")]
        public JObject Metadata { get; set; }
    }

    public class FurniturePlacementResult
    {
        [JsonProperty("status")]
        public string Status { get; set; }

        [JsonProperty("message")]
        public string Message { get; set; }

        [JsonProperty("asset_id")]
        public string AssetId { get; set; }

        [JsonProperty("object_guid")]
        public string ObjectGuid { get; set; }

        [JsonProperty("block_definition")]
        public string BlockDefinition { get; set; }

        [JsonProperty("definition_created")]
        public bool DefinitionCreated { get; set; }

        [JsonProperty("bounds")]
        public BoundsPayload Bounds { get; set; }

        [JsonProperty("error_trace")]
        public string ErrorTrace { get; set; }

        [JsonProperty("error_code", NullValueHandling = NullValueHandling.Ignore)]
        public string ErrorCode { get; set; }

        [JsonProperty("needs_refresh", DefaultValueHandling = DefaultValueHandling.Ignore)]
        public bool NeedsRefresh { get; set; }

        [JsonProperty("mutation_state")]
        public string MutationState { get; set; } = "not_started";

        [JsonProperty("requires_reconciliation", DefaultValueHandling = DefaultValueHandling.Ignore)]
        public bool RequiresReconciliation { get; set; }

        [JsonProperty("link_type", NullValueHandling = NullValueHandling.Ignore)]
        public string LinkType { get; set; }

        [JsonProperty("layer_style", NullValueHandling = NullValueHandling.Ignore)]
        public string LayerStyle { get; set; }

        [JsonProperty("source_path", NullValueHandling = NullValueHandling.Ignore)]
        public string SourcePath { get; set; }

        [JsonProperty("source_sha256", NullValueHandling = NullValueHandling.Ignore)]
        public string SourceSha256 { get; set; }

        [JsonProperty("metadata_scope", NullValueHandling = NullValueHandling.Ignore)]
        public string MetadataScope { get; set; }

        [JsonProperty("definition_refreshed", DefaultValueHandling = DefaultValueHandling.Ignore)]
        public bool DefinitionRefreshed { get; set; }

        [JsonProperty("affected_existing_instances", DefaultValueHandling = DefaultValueHandling.Ignore)]
        public int AffectedExistingInstances { get; set; }
    }

    public class BoundsPayload
    {
        [JsonProperty("min")]
        public double[] Min { get; set; }

        [JsonProperty("max")]
        public double[] Max { get; set; }

        public static BoundsPayload FromBoundingBox(BoundingBox bounds)
        {
            if (!bounds.IsValid)
                return null;
            return new BoundsPayload
            {
                Min = new[] { bounds.Min.X, bounds.Min.Y, bounds.Min.Z },
                Max = new[] { bounds.Max.X, bounds.Max.Y, bounds.Max.Z }
            };
        }
    }
}
