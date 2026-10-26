"""Register portable asset exchange tools and their native report helpers."""
from almond_mcp.tool_response import error_payload
from almond_mcp.instruction_text import tool_instruction, read_instruction

import hashlib
import json
from pathlib import Path
import uuid

from almond_mcp.features.modeling import modeling_setup
from almond_mcp import paths


def register(mcp, context):
    """Register exchange tools against the calling server's live context."""

    def _restore_and_place_script(contract: dict, materials: dict[str, dict],
                                  x_mm: float, y_mm: float, z_mm: float,
                                  rotation_degrees: float, layer: str) -> str:
        """C# run after a GLB import: restore metadata, correct the colour drift,
    collapse duplicate materials, then place per the contract anchor."""
        lib_rows = []
        for material_id, material in materials.items():
            resolved = modeling_setup.recipe(material)
            # Reuse a recipe revision, not a color-shifted material from the imported GLB.
            revision = hashlib.sha256(json.dumps(resolved, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()[:12]
            resolved["name"] += f" ({revision})"
            values = [material_id, material["name"], material["category"], material["ue_material_slot"],
                      *material["base_color"], material["metallic"], material["roughness"], material["opacity"]]
            encoded = ", ".join(json.dumps(v, ensure_ascii=True) for v in values)
            encoded += ", " + modeling_setup.literal(resolved)
            for alias in dict.fromkeys((context.exchange.material_name(material_id), material["name"], resolved["name"])):
                lib_rows.append("{ " + json.dumps(alias, ensure_ascii=True) + ", new object[] { " + encoded + " } }")
        anchor = contract["spatial"].get("anchor", "bottom_center")
        # Library GLBs hold numeric millimetres, but Rhino's glTF import reads metres.
        convention = (contract.get("passport") or {}).get("coordinate_convention") or {}
        glb_scale = 0.001 if convention.get("glb_numeric_units") == "mm" else 1.0
        passport_stamp = ""
        if contract.get("passport"):
            # C# verbatim string, so quotes/backslashes in provenance stay data.
            encoded = json.dumps(contract["passport"], ensure_ascii=True).replace('"', '""')
            passport_stamp = f'attributes.SetUserString("almond:passport", @"{encoded}");'
        return f"""
using System;
using System.Collections.Generic;
using System.Linq;
using Rhino;
using Rhino.Geometry;
using Rhino.DocObjects;
using Rhino.Display;

public class Script
{{
    // material name -> {{ id, name, category, ue_slot, r, g, b, metallic, roughness, opacity }}
    static readonly Dictionary<string, object[]> Lib = new Dictionary<string, object[]>
    {{
        {",\n        ".join(lib_rows) if lib_rows else ""}
    }};

    public static List<Guid> Run(RhinoDoc doc)
    {{
        var imported = new List<RhinoObject>();
        foreach (string s in new[] {{ {", ".join('"%s"' % g for g in contract["_imported_guids"])} }})
        {{
            var o = doc.Objects.FindId(new Guid(s));
            if (o != null) imported.Add(o);
        }}
        if (imported.Count == 0) return new List<Guid>();

        // Resolve only imported objects through the shared MCP material implementation.
        var canonical = new Dictionary<string, int>();
        int deduped = 0;
        foreach (var obj in imported)
        {{
            var mat = obj.GetMaterial(true);
            if (mat == null || !Lib.TryGetValue(mat.Name, out var spec)) continue;
            string id = (string)spec[0];
            if (!canonical.ContainsKey(id))
            {{
                using var attributes = RhinoAlmondBridge.ModelingMaterials.CreateAttributes(
                    doc, (string)spec[10], attachMetadata: false, reuseLegacyMaterial: false);
                canonical[id] = attributes.MaterialIndex;
            }}
        }}
        int layerIndex = RhinoAlmondBridge.DocumentLayers.Ensure(doc, {json.dumps(layer, ensure_ascii=True)});

        // 3. re-attach the metadata glTF dropped, keyed off the surviving name
        int stamped = 0;
        foreach (var obj in imported)
        {{
            var attributes = obj.Attributes.Duplicate();
            var mat = obj.GetMaterial(true);
            string matName = mat != null ? mat.Name : "";
            if (matName.Length > 0 && Lib.ContainsKey(matName))
            {{
                var spec = Lib[matName];
                string id = (string)spec[0];
                if (attributes.MaterialIndex != canonical[id])
                {{
                    attributes.MaterialIndex = canonical[id];
                    deduped++;
                }}
                attributes.MaterialSource = ObjectMaterialSource.MaterialFromObject;
                attributes.SetUserString("almond:material_id", (string)spec[0]);
                attributes.ObjectColor = System.Drawing.Color.FromArgb((int)spec[4], (int)spec[5], (int)spec[6]);
                attributes.ColorSource = ObjectColorSource.ColorFromObject;
                stamped++;
            }}
            attributes.SetUserString("almond:asset_id", "{contract['asset_id']}");
            attributes.SetUserString("almond:source_app", "{contract.get('source_app', 'unknown')}");
            {passport_stamp}
            attributes.LayerIndex = layerIndex;
            if (!doc.Objects.ModifyAttributes(obj.Id, attributes, true)) throw new InvalidOperationException("Cannot restore imported attributes.");
        }}

        // 4. place per the contract anchor, in this document's units
        double toDoc = RhinoMath.UnitScale(UnitSystem.Millimeters, doc.ModelUnitSystem);
        var scale = Transform.Scale(Point3d.Origin, {glb_scale!r});
        var bb = BoundingBox.Empty;
        foreach (var o in imported) bb.Union(o.Geometry.GetBoundingBox(true));
        bb.Transform(scale);
        var anchorPt = new Point3d((bb.Min.X + bb.Max.X) / 2, (bb.Min.Y + bb.Max.Y) / 2,
            "{anchor}" == "center" ? (bb.Min.Z + bb.Max.Z) / 2 : bb.Min.Z);
        var target = new Point3d({x_mm} * toDoc, {y_mm} * toDoc, {z_mm} * toDoc);
        var xform = Transform.Translation(target - anchorPt);
        if (Math.Abs({rotation_degrees}) > 1e-9)
            xform = xform * Transform.Rotation(RhinoMath.ToRadians({rotation_degrees}), Vector3d.ZAxis, anchorPt);
        xform = xform * scale;
        foreach (var o in imported) doc.Objects.Transform(o.Id, xform, true);

        // 5. measure what actually landed, for the contract dimension check
        var after = BoundingBox.Empty;
        foreach (var o in imported)
        {{
            var refreshed = doc.Objects.FindId(o.Id);
            if (refreshed != null) after.Union(refreshed.Geometry.GetBoundingBox(true));
        }}
        double toMM = RhinoMath.UnitScale(doc.ModelUnitSystem, UnitSystem.Millimeters);
        RhinoApp.WriteLine(string.Format(
            "ALMOND_IMPORT stamped={{0}} deduped={{1}} w={{2:F1}} d={{3:F1}} h={{4:F1}}",
            stamped, deduped,
            (after.Max.X - after.Min.X) * toMM,
            (after.Max.Y - after.Min.Y) * toMM,
            (after.Max.Z - after.Min.Z) * toMM));
        System.IO.File.WriteAllText(
            System.IO.Path.Combine(System.IO.Path.GetTempPath(), "almond_import_report.json"),
            "{{\\"stamped\\":" + stamped + ",\\"deduped\\":" + deduped
            + ",\\"width\\":" + ((after.Max.X - after.Min.X) * toMM).ToString("F1")
            + ",\\"depth\\":" + ((after.Max.Y - after.Min.Y) * toMM).ToString("F1")
            + ",\\"height\\":" + ((after.Max.Z - after.Min.Z) * toMM).ToString("F1") + "}}");
        doc.Views.Redraw();
        return imported.Select(o => o.Id).ToList();
    }}
}}
"""


    @mcp.tool()
    @tool_instruction(__file__, 'export_asset_contract')
    def export_asset_contract(
        guids: list[str],
        asset_id: str,
        name: str = "",
        output_dir: str = "",
    ) -> str:
        if not guids:
            return json.dumps(error_payload("At least one GUID is required."))
        try:
            target_dir = Path(output_dir) if output_dir else paths.user_data_dir() / "exchange"
            glb_path, contract_path = context.exchange.contract_paths(target_dir, asset_id)
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))

        payload = json.dumps({
            "type": "export_glb",
            "guids": guids,
            "output_path": str(glb_path),
        }).encode("utf-8")
        try:
            result = json.loads(context._send_and_receive(payload, timeout=90.0))
        except ConnectionRefusedError:
            return json.dumps(error_payload("Rhino bridge is unavailable."))
        except Exception as exc:
            return json.dumps(error_payload(f"GLB export failed: {exc}"))
        if result.get("status") != "success":
            return json.dumps(result)

        bounds = result.get("bounds") or {}
        if not bounds:
            return json.dumps(error_payload("Export returned no bounds."))
        # export_glb reports bounds in document units
        unit_scale = {"Millimeters": 1.0, "Centimeters": 10.0, "Meters": 1000.0,
                      "Inches": 25.4, "Feet": 304.8}.get(result.get("units", "Millimeters"), 1.0)
        bounds_mm = {
            "min": [float(v) * unit_scale for v in bounds["min"]],
            "max": [float(v) * unit_scale for v in bounds["max"]],
        }
        material_groups = context._material_groups(guids)
        try:
            contract = context.exchange.build_contract(
                asset_id=asset_id,
                name=name or asset_id,
                glb_filename=glb_path.name,
                bounds_mm=bounds_mm,
                materials=material_groups,
                source_app="rhino",
                object_count=len(result.get("object_guids", guids)),
            )
        except ValueError as exc:
            return json.dumps(error_payload(str(exc)))
        contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        return json.dumps({
            "status": "success",
            "asset_id": asset_id,
            "glb_path": str(glb_path),
            "contract_path": str(contract_path),
            "dimensions_mm": contract["dimensions_mm"],
            "materials": material_groups,
            "next_step": read_instruction(__file__, 'response-672'),
        })


    def _material_groups(guids: list[str]) -> list[dict]:
        """Resolve actual ByObject/ByLayer materials, including readable library names."""
        names = ", ".join("{ " + json.dumps(m["name"], ensure_ascii=True) + ", " + json.dumps(mid) + " }"
                          for mid, m in context.material_library.materials.items())
        script = """
using System;
using System.Collections.Generic;
using System.IO;
using Rhino;
public class Script
{
    public static object Run(RhinoDoc doc)
    {
        var names = new Dictionary<string, string> { %s };
        var rows = new List<string>();
        foreach (string s in new[] { %s })
        {
            var obj = doc.Objects.FindId(new Guid(s));
            if (obj == null) continue;
            var mat = obj.GetMaterial(true);
            string mid = mat == null ? null : mat.GetUserString("almond:material_id");
            string name = obj.GetRenderMaterial(true)?.Name ?? mat?.Name ?? "";
            if (string.IsNullOrEmpty(mid)) names.TryGetValue(name, out mid);
            if (string.IsNullOrEmpty(mid) && name.StartsWith("ALMOND::"))
                mid = name.Substring(8).Split(new[] { "::" }, StringSplitOptions.None)[0];
            if (!string.IsNullOrEmpty(mid)) rows.Add(mid + "|" + s);
        }
        File.WriteAllLines(Path.Combine(Path.GetTempPath(), "almond_matgroups.txt"), rows);
        return new { recorded = rows.Count };
    }
}
""" % (names, ", ".join(json.dumps(str(uuid.UUID(g))) for g in guids))
        try:
            context._send_and_receive(json.dumps({"type": "execute", "script": script}).encode("utf-8"),
                              timeout=45.0)
            report = Path(context.tempfile.gettempdir()) / "almond_matgroups.txt"
            groups: dict[str, list[str]] = {}
            if report.is_file():
                for line in report.read_text(encoding="utf-8").splitlines():
                    if "|" in line:
                        material_id, guid = line.split("|", 1)
                        groups.setdefault(material_id, []).append(guid)
            return [{"material_id": k, "objects": v} for k, v in sorted(groups.items())]
        except Exception:
            return []


    @mcp.tool()
    @tool_instruction(__file__, 'import_asset_contract')
    def import_asset_contract(
        contract_path: str,
        x_mm: float = 0,
        y_mm: float = 0,
        z_mm: float = 0,
        rotation_degrees: float = 0,
        layer: str = "ALMOND-EXCHANGE",
    ) -> str:
        try:
            contract = context.exchange.load_contract(contract_path)
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))
        return json.dumps(context._receive_contract(contract, x_mm, y_mm, z_mm, rotation_degrees, layer))


    def _receive_contract(contract: dict, x_mm: float, y_mm: float, z_mm: float,
                          rotation_degrees: float, layer: str) -> dict:
        """Import a loaded contract's GLB into Rhino, restore materials and
    metadata, place it per the contract anchor, and report the dimension
    check. Shared by import_asset_contract and place_generated_asset."""
        problem = modeling_setup.check_bridge(context._send_and_receive)
        if problem:
            return problem
        import_script = """
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Rhino;

public class Script
{
    public static List<Guid> Run(RhinoDoc doc)
    {
        var before = new HashSet<Guid>(doc.Objects.Select(o => o.Id));
        RhinoApp.RunScript("_-Import \\"%s\\" _Enter", false);
        var added = doc.Objects.Where(o => !before.Contains(o.Id)).Select(o => o.Id).ToList();
        File.WriteAllLines(Path.Combine(Path.GetTempPath(), "almond_imported.txt"),
            added.Select(g => g.ToString()));
        return added;
    }
}
""" % contract["_resolved_file"].replace("\\", "\\\\")
        try:
            result = json.loads(context._send_and_receive(
                json.dumps({"type": "execute", "script": import_script}).encode("utf-8"),
                timeout=120.0))
        except ConnectionRefusedError:
            return error_payload("Rhino bridge is unavailable.")
        except Exception as exc:
            return error_payload(f"Import failed: {exc}")
        if result.get("status") != "success":
            return result
        imported = result.get("guids") or []
        if not imported:
            return error_payload("Rhino imported no objects from the GLB.")

        contract["_imported_guids"] = imported
        needed = {row["material_id"] for row in contract.get("materials", [])}
        library = {mid: context.material_library.get(mid) for mid in needed}
        known = {mid: spec for mid, spec in library.items() if spec}
        unknown = sorted(mid for mid, spec in library.items() if not spec)

        script = context._restore_and_place_script(contract, known, x_mm, y_mm, z_mm,
                                           rotation_degrees, layer)
        try:
            restore = json.loads(context._send_and_receive(
                json.dumps({"type": "execute", "script": script}).encode("utf-8"),
                timeout=120.0))
        except Exception as exc:
            return {"status": "error",
                               "message": f"Imported, but restore/place failed: {exc}",
                               "imported_guids": imported}
        if restore.get("status") != "success":
            return {"status": "error", "message": restore.get("message", "restore failed"),
                               "imported_guids": imported}

        report_path = Path(context.tempfile.gettempdir()) / "almond_import_report.json"
        report = {}
        if report_path.is_file():
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
            except ValueError:
                report = {}
        check = context.exchange.dimension_report(contract, report) if report else {"status": "unknown"}
        return {
            "status": "success",
            "asset_id": contract["asset_id"],
            "source_app": contract.get("source_app", "unknown"),
            "imported_count": len(imported),
            "metadata_restored": report.get("stamped", 0),
            "materials_deduplicated": report.get("deduped", 0),
            "unknown_material_ids": unknown,
            "dimension_check": check,
            "layer": layer,
            "imported_guids": imported,
        }


    @mcp.tool()
    @tool_instruction(__file__, 'get_blender_helper_script')
    def get_blender_helper_script(action: str, asset_id: str = "", name: str = "",
                                  output_dir: str = "", material_id: str = "",
                                  object_names: list[str] | None = None) -> str:
        action = action.strip().lower()
        if action == "export":
            if not asset_id:
                return json.dumps(error_payload("asset_id is required for export."))
            target = output_dir or str(paths.user_data_dir() / "exchange")
            return json.dumps({
                "status": "success",
                "action": "export",
                "script": context.exchange.blender_export_script(asset_id, name or asset_id, target),
                "note": read_instruction(__file__, 'response-677'),
            })
        if action == "materials":
            material = context.material_library.get(material_id)
            if not material:
                return json.dumps(error_payload(read_instruction(__file__, 'response-679').format(material_id)))
            if not object_names:
                return json.dumps(error_payload("object_names is required."))
            script = context.exchange.blender_material_script(
                [material], [{"material_id": material_id, "objects": object_names}])
            return json.dumps({"status": "success", "action": "materials", "script": script})
        return json.dumps(error_payload('action must be "export" or "materials".'))


    return {
        "_restore_and_place_script": _restore_and_place_script,
        "export_asset_contract": export_asset_contract,
        "_material_groups": _material_groups,
        "import_asset_contract": import_asset_contract,
        "_receive_contract": _receive_contract,
        "get_blender_helper_script": get_blender_helper_script,
    }
