"""Provide private asset placement and native report helpers."""
from dataclasses import dataclass
import tempfile
from typing import Callable

from almond_mcp.tool_response import error_payload

import hashlib
import json
from pathlib import Path
import uuid

from almond_mcp.features.modeling import modeling_setup
from almond_mcp.features.modeling.library import MaterialLibrary
from almond_mcp.features.assets.mutation import send_mutation, unresolved
from . import exchange


@dataclass(frozen=True)
class ExchangeReports:
    directory: Path
    managed: bool = False


def local_exchange_reports() -> ExchangeReports:
    return ExchangeReports(Path(tempfile.gettempdir()))


@dataclass(frozen=True)
class Exchange:
    send: Callable[..., str]
    material_library: MaterialLibrary
    report_files: Callable[[], ExchangeReports] = local_exchange_reports
    dimension_report: Callable[[dict, dict], dict] = exchange.dimension_report

    @staticmethod
    def _restore_and_place_script(contract: dict, materials: dict[str, dict],
                                  x_mm: float, y_mm: float, z_mm: float,
                                  rotation_degrees: float, layer: str, report_path: Path) -> str:
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
            for alias in dict.fromkeys((exchange.material_name(material_id), material["name"], resolved["name"])):
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

    public static object Run(RhinoDoc doc)
    {{
        var imported = new List<RhinoObject>();
        foreach (string s in new[] {{ {", ".join('"%s"' % g for g in contract["_imported_guids"])} }})
        {{
            var o = doc.Objects.FindId(new Guid(s));
            if (o != null) imported.Add(o);
        }}
        if (imported.Count == 0) return new {{ restored_count = 0 }};

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
            {json.dumps(str(report_path), ensure_ascii=True)},
            "{{\\"stamped\\":" + stamped + ",\\"deduped\\":" + deduped
            + ",\\"width\\":" + ((after.Max.X - after.Min.X) * toMM).ToString("F1")
            + ",\\"depth\\":" + ((after.Max.Y - after.Min.Y) * toMM).ToString("F1")
            + ",\\"height\\":" + ((after.Max.Z - after.Min.Z) * toMM).ToString("F1") + "}}");
        doc.Views.Redraw();
        return new {{ restored_count = imported.Count }};
    }}
}}
"""


    def material_groups(self, guids: list[str]) -> list[dict]:
        """Resolve actual ByObject/ByLayer materials, including readable library names."""
        reports = self.report_files()
        report = reports.directory / f"almond_matgroups_{uuid.uuid4().hex}.txt"
        names = ", ".join("{ " + json.dumps(m["name"], ensure_ascii=True) + ", " + json.dumps(mid) + " }"
                          for mid, m in self.material_library.materials.items())
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
        File.WriteAllLines(%s, rows);
        return new { recorded = rows.Count };
    }
}
""" % (names, ", ".join(json.dumps(str(uuid.UUID(g))) for g in guids), json.dumps(str(report), ensure_ascii=True))
        try:
            self.send(json.dumps({"type": "execute", "script": script}).encode("utf-8"), timeout=45.0)
            groups: dict[str, list[str]] = {}
            if report.is_file():
                for line in report.read_text(encoding="utf-8").splitlines():
                    if "|" in line:
                        material_id, guid = line.split("|", 1)
                        groups.setdefault(material_id, []).append(guid)
        except Exception:
            if reports.managed and not report.is_file():
                raise RuntimeError("Rhino material report was not received; export metadata is unverified.")
            return []
        if reports.managed and not report.is_file():
            raise RuntimeError("Rhino material report was not received; export metadata is unverified.")
        if not reports.managed and report.is_file():
            try:
                report.unlink()
            except OSError:
                pass
        return [{"material_id": k, "objects": v} for k, v in sorted(groups.items())]


    def receive_contract(self, contract: dict, x_mm: float, y_mm: float, z_mm: float,
                          rotation_degrees: float, layer: str) -> dict:
        """Import a loaded contract's GLB into Rhino, restore materials and
    metadata, place it per the contract anchor, and report the dimension
    check for the generated-library place_asset helper."""
        problem = modeling_setup.check_bridge(self.send)
        if problem:
            return problem
        # A unique pair is required even outside the managed runtime. The same
        # absolute paths are embedded in the native scripts and read here.
        token = uuid.uuid4().hex
        reports = self.report_files()
        receipt = reports.directory / f"almond_imported_{token}.txt"
        report_path = reports.directory / f"almond_import_report_{token}.json"
        managed = reports.managed
        import_script = """
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Rhino;

public class Script
{
    public static object Run(RhinoDoc doc)
    {
        var before = new HashSet<Guid>(doc.Objects.Select(o => o.Id));
        RhinoApp.RunScript("_-Import \\"%s\\" _Enter", false);
        var added = doc.Objects.Where(o => !before.Contains(o.Id)).Select(o => o.Id).ToList();
        File.WriteAllLines(%s,
            added.Select(g => g.ToString()));
        return new { imported_count = added.Count };
    }
}
""" % (contract["_resolved_file"].replace("\\", "\\\\"), json.dumps(str(receipt), ensure_ascii=True))
        result = send_mutation(self.send, json.dumps({"type": "execute", "script": import_script}).encode("utf-8"),
                               timeout=120.0, action="Import")
        if result.get("mutation_state") == "not_started":
            return result
        # Receipts provide evidence even after reply loss. Only a matching
        # completed reply authorizes the second native mutation.
        try:
            with receipt.open("rb") as handle:
                data = handle.read(2_097_153)
            if len(data) > 2_097_152:
                raise ValueError("Import receipt exceeds 2 MiB")
            imported = [str(uuid.UUID(line)) for line in data.decode("utf-8-sig").splitlines()]
            if len(set(imported)) != len(imported):
                raise ValueError("Import receipt has duplicate object IDs")
        except (OSError, ValueError) as exc:
            if result["status"] != "success":
                return result
            return unresolved(f"Import object receipt could not be read: {exc}", reply=result)
        if result["status"] != "success":
            return unresolved(result["message"], reply=result, imported_guids=imported)
        observation = result.get("result")
        if (not isinstance(observation, dict) or type(observation.get("imported_count")) is not int
                or observation["imported_count"] != len(imported)):
            return unresolved("Import receipt and native result did not confirm the same objects. Inspect Rhino before continuing.",
                              reply=result, imported_guids=imported)
        if not imported:
            if not managed:
                try:
                    receipt.unlink(missing_ok=True)
                except OSError:
                    pass
            return error_payload("Rhino imported no objects from the GLB.")

        try:
            needed = {row["material_id"] for row in contract.get("materials", [])}
            library = {mid: self.material_library.get(mid) for mid in needed}
            known = {mid: spec for mid, spec in library.items() if spec}
            unknown = sorted(mid for mid, spec in library.items() if not spec)
            script = self._restore_and_place_script({**contract, "_imported_guids": imported}, known, x_mm, y_mm, z_mm,
                                                    rotation_degrees, layer, report_path)
        except Exception as exc:
            return unresolved(f"Imported, but restore/place could not be prepared: {exc}", imported_guids=imported, partial=True)
        restore = send_mutation(self.send, json.dumps({"type": "execute", "script": script}).encode("utf-8"),
                                timeout=120.0, action="Restore/place")
        if restore.get("status") != "success":
            return unresolved(restore.get("message", "Restore/place failed"), reply=restore, imported_guids=imported, partial=True)
        if (restore.get("result_error") or not isinstance(restore.get("result"), dict)
                or type(restore["result"].get("restored_count")) is not int
                or restore["result"].get("restored_count") != len(imported)):
            return unresolved("Restore/place result could not be confirmed. Inspect the imported objects before continuing.",
                              reply=restore, imported_guids=imported, partial=True)

        try:
            raw_report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw_report = None
        report = raw_report if isinstance(raw_report, dict) else {}
        if managed and not {"stamped", "deduped", "width", "depth", "height"} <= report.keys():
            return unresolved('Geometry was imported, but its report is unverified. Inspect the existing objects before any retry.',
                              reply={"report_path": str(report_path)}, imported_guids=imported, partial=True)
        check = self.dimension_report(contract, report) if report else {"status": "unknown"}
        if report and not managed:
            # Both native calls returned and their output was read. On any
            # uncertain outcome leave the files for inspection/late writes.
            for path in (receipt, report_path):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
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
