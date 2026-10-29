# -*- coding: utf-8 -*-
"""Rhino 8: _-RunPythonScript. Contract and limitations: SPEC.md."""
import json
import math
import os
import re
import uuid
import clr
import Rhino as R
import System
from System.Drawing import Color
from System.Collections.Generic import List

G = R.Geometry
D = R.DocObjects
CLIP_LAYER = 'setting::clipping::Section'
SECTION_LAYER = 'Drawing::Section'
HATCH_LAYER = 'D::Hatch::Pattern'
ELEVATION_LAYER = 'Drawing::Elevation'
OWNER = 'PlanSection/2'
try:
    STRING_TYPES = (basestring,)
except NameError:
    STRING_TYPES = (str,)


def objects(doc):
    s = D.ObjectEnumeratorSettings()
    s.NormalObjects = s.HiddenObjects = s.LockedObjects = True
    s.ReferenceObjects = True
    s.DeletedObjects = s.IdefObjects = False
    return list(doc.Objects.GetObjectList(s))


def clipping_planes(doc):
    return sorted([o for o in objects(doc) if isinstance(o, D.ClippingPlaneObject)],
                  key=lambda o: ((o.Name or '').lower(), str(o.Id)), reverse=True)


def finite(value):
    return not (math.isnan(value) or math.isinf(value))


def draft_plane(text):
    if not text:
        return G.Plane.WorldXY
    data = json.loads(text)
    values = [data[k] for k in ('origin', 'xaxis', 'yaxis')]
    if any(len(v) != 3 or not all(finite(float(n)) for n in v) for v in values):
        raise ValueError('draft_plane requires three finite XYZ vectors')
    p = G.Plane(G.Point3d(*values[0]), G.Vector3d(*values[1]), G.Vector3d(*values[2]))
    if not p.IsValid:
        raise ValueError('Invalid draft_plane axes')
    return p


def plane_json(p):
    return json.dumps(dict(origin=[p.OriginX, p.OriginY, p.OriginZ],
                           xaxis=[p.XAxis.X, p.XAxis.Y, p.XAxis.Z],
                           yaxis=[p.YAxis.X, p.YAxis.Y, p.YAxis.Z]))


def relative_style(distance, nearest, farthest, near_width, far_width, near_dark, far_dark):
    t = 0.0 if farthest <= nearest else max(0.0, min(1.0, (distance-nearest)/(farthest-nearest)))
    width = near_width + (far_width-near_width)*t
    gray = int(round(255.0*(1.0-(near_dark+(far_dark-near_dark)*t)/100.0)))
    return round(width, 8), gray


def validate_options(near_width, far_width, near_dark, far_dark):
    if not all(finite(x) for x in (near_width, far_width, near_dark, far_dark)):
        raise ValueError('Style values must be finite')
    if not 0 < far_width <= near_width or not 0 <= far_dark <= near_dark <= 100:
        raise ValueError('Require 0 < FarWidth <= NearWidth; 0 <= FarDark <= NearDark <= 100')


def read_clip(doc, cp, target=None):
    geo = cp.ClippingPlaneGeometry
    if not geo.Plane.IsValid:
        raise ValueError('Invalid clipping plane')
    depth = geo.PlaneDepth if geo.PlaneDepthEnabled else None
    if depth is not None and (not finite(depth) or depth < 0):
        raise ValueError('Enabled depth must be nonnegative and finite')
    ids, layers, exclude = geo.GetClipParticipation()
    ids, layers = set(ids), set(layers)
    enabled = geo.ParticipationListsEnabled and not cp.IsReference
    if enabled:
        if any(doc.Objects.FindId(i) is None for i in ids):
            raise ValueError('Clipping participation references a missing object')
        if any(i < 0 or i >= doc.Layers.Count or doc.Layers[i].IsDeleted for i in layers):
            raise ValueError('Clipping participation references a missing layer')
    placement = target if target is not None else draft_plane(cp.Attributes.GetUserString('draft_plane'))
    if not placement.IsValid:
        raise ValueError('Invalid placement plane')
    return dict(plane=geo.Plane, depth=depth, target=placement, ids=ids, layers=layers,
                exclude=exclude, enabled=enabled)


def resolved_attributes(doc, original, parents=()):
    """Resolve only drawing properties; never copy reference/lock/group state."""
    chain = [original]+list(reversed(parents))
    def owner(field):
        return next((a for a in chain if not str(getattr(a, field)).endswith('FromParent')), chain[-1])
    a = D.ObjectAttributes()
    a.LayerIndex = original.LayerIndex
    color = owner('ColorSource')
    a.ObjectColor = color.DrawColor(doc)
    a.ColorSource = D.ObjectColorSource.ColorFromObject
    plot = owner('PlotColorSource')
    # FromDisplay must resolve the display source in the same ancestor context.
    if plot.PlotColorSource == D.ObjectPlotColorSource.PlotColorFromDisplay:
        index = next(i for i, item in enumerate(chain) if item is plot)
        display = next((item for item in chain[index:] if item.ColorSource != D.ObjectColorSource.ColorFromParent), chain[-1])
        a.PlotColor = display.DrawColor(doc)
    else:
        a.PlotColor = plot.ComputedPlotColor(doc)
    a.PlotColorSource = D.ObjectPlotColorSource.PlotColorFromObject
    a.PlotWeight = owner('PlotWeightSource').ComputedPlotWeight(doc)
    a.PlotWeightSource = D.ObjectPlotWeightSource.PlotWeightFromObject
    line = owner('LinetypeSource')
    a.LinetypeIndex = (line.LinetypeIndex if line.LinetypeSource == D.ObjectLinetypeSource.LinetypeFromObject
                      else doc.Layers[line.LayerIndex].LinetypeIndex)
    a.LinetypeSource = D.ObjectLinetypeSource.LinetypeFromObject
    a.LinetypePatternScale = line.LinetypePatternScale
    custom = line.GetCustomLinetype() if line.LinetypeSource == D.ObjectLinetypeSource.LinetypeFromObject else None
    if custom is not None: a.SetCustomLinetype(custom)
    section = owner('SectionAttributesSource')
    source = section.SectionAttributesSource
    if source == D.ObjectSectionAttributesSource.FromSectioner:
        raise ValueError('SectionStyle FromSectioner is not supported on source layer '+doc.Layers[original.LayerIndex].FullPath)
    style = (section.GetCustomSectionStyle() if source == D.ObjectSectionAttributesSource.FromObject
             else doc.Layers[section.LayerIndex].GetCustomSectionStyle())
    if style is not None:
        style = D.SectionStyle(style)
        if style.HatchIndex != R.RhinoMath.UnsetIntIndex:
            pattern = hatch_pattern(doc, style.HatchIndex)
            if pattern.Index != style.HatchIndex:
                a.SetUserString('ps:hatch_fallback', str(style.HatchIndex))
                style.HatchIndex = pattern.Index
        a.SetCustomSectionStyle(style)
    a.SectionAttributesSource = D.ObjectSectionAttributesSource.FromObject
    return a


def hatch_pattern(doc, index):
    pattern = doc.HatchPatterns.FindIndex(index)
    if pattern is None or pattern.IsDeleted:
        pattern = doc.HatchPatterns.FindName('Solid') or D.HatchPattern.Defaults.Solid
    return pattern


def style_key(a):
    style, line = a.GetCustomSectionStyle(), a.GetCustomLinetype()
    return (a.LayerIndex, a.ObjectColor.ToArgb(), a.PlotColor.ToArgb(), a.PlotWeight,
            a.LinetypeIndex, a.LinetypePatternScale,
            int(line.DataCRC(0)) if line is not None else None,
            int(style.DataCRC(0)) if style is not None else None)


def record_bounds(record):
    """Exact world bounds shared by section culling and elevation styling."""
    bounds = record.get('bounds')
    if bounds is None:
        bounds = record['geometry'].GetBoundingBox(True)
        record['bounds'] = bounds
    return bounds


def meets_plane(bounds, plane, tol):
    distances = [plane.DistanceTo(p) for p in bounds.GetCorners()]
    return min(distances) <= tol and max(distances) >= -tol


def section_tolerance(doc):
    """Keep cut topology and its overlap cleanup at the same physical accuracy."""
    return min(doc.ModelAbsoluteTolerance,
               .01*R.RhinoMath.UnitScale(R.UnitSystem.Millimeters, doc.ModelUnitSystem))


def input_entry(geometry, transform):
    valid = geometry.IsValid
    bounds = geometry.GetBoundingBox(True) if valid else None
    if bounds is not None: bounds.Transform(transform)
    return dict(valid=valid, cull_bounds=bounds, prepared=False, geometry=None)


def transform_values(transform):
    return (transform.M00,transform.M01,transform.M02,transform.M03,
            transform.M10,transform.M11,transform.M12,transform.M13,
            transform.M20,transform.M21,transform.M22,transform.M23,
            transform.M30,transform.M31,transform.M32,transform.M33)


class ModelCache(object):
    """Own lazy world geometry for one command; never cache resolved attributes."""
    def __init__(self, doc):
        self.document = doc.RuntimeSerialNumber
        self.entries = {}
        self.closed = False

    def check(self, doc):
        if self.closed or self.document != doc.RuntimeSerialNumber:
            raise ValueError('Invalid PlanSection model cache')

    def get(self, obj, transform, source, matrix):
        key = (source, int(obj.RuntimeSerialNumber), matrix)
        entry = self.entries.get(key)
        if entry is None:
            entry = self.entries[key] = input_entry(obj.Geometry, transform)
        return entry

    def Dispose(self):
        if self.closed: return
        self.closed = True
        for entry in self.entries.values():
            if entry['geometry'] is not None: entry['geometry'].Dispose()
        self.entries.clear()


def world_geometry(original, transform):
    """Create one owned world copy, releasing intermediate conversion geometry."""
    geo = original.Duplicate()
    try:
        if isinstance(geo, G.SubD):
            subd, geo = geo, None
            try:
                geo = subd.ToBrep()
                if geo is None or not geo.IsValid:
                    if geo is not None: geo.Dispose()
                    geo = None
                    geo = subd.ToBrep(G.SubDToBrepOptions.DefaultPacked)
            finally:
                subd.Dispose()
        elif isinstance(geo, (G.Extrusion, G.Surface)):
            surface, geo = geo, None
            try:
                geo = surface.ToBrep()
            finally:
                surface.Dispose()
        if geo is not None and (not geo.Transform(transform) or not geo.IsValid):
            geo.Dispose()
            geo = None
        return geo
    except:
        if geo is not None: geo.Dispose()
        raise


def model_objects(doc, clip, issues, model_cache=None):
    """Return fresh provenance/styles with owned or command-cache world geometry."""
    if model_cache is not None: model_cache.check(doc)
    records = []

    def walk(obj, transform, matrix, path, inherited, definitions, parents):
        if obj.Attributes.GetUserString('ps:generator') == OWNER:
            return
        match = inherited or obj.Id in clip['ids'] or obj.Attributes.LayerIndex in clip['layers']
        if clip['enabled'] and clip['exclude'] and match:
            return
        if isinstance(obj, D.InstanceObject):
            idef = obj.InstanceDefinition
            if idef is None or idef.Id in definitions:
                raise ValueError('Missing or cyclic block definition: '+str(obj.Id))
            child_transform = transform*obj.InstanceXform
            child_matrix = transform_values(child_transform) if model_cache is not None else None
            child_path = path+[str(obj.Id)]
            child_definitions, child_parents = definitions+[idef.Id], parents+[obj.Attributes]
            for child in idef.GetObjects():
                walk(child, child_transform, child_matrix, child_path, match,
                     child_definitions, child_parents)
            return
        if clip['enabled'] and not clip['exclude'] and not match:
            return
        geo = obj.Geometry
        if not isinstance(geo, (G.Brep, G.Surface, G.Extrusion, G.SubD, G.Mesh)) or isinstance(geo, G.ClippingPlaneSurface):
            issues['unsupported'] = issues.get('unsupported', 0)+1
            return
        source = '/'.join(path+[str(obj.Id)])
        entry = (model_cache.get(obj, transform, source, matrix) if model_cache is not None
                 else input_entry(geo, transform))
        if not entry['valid']:
            issues['invalid'] = issues.get('invalid', 0)+1
            return
        # Keep the original conservative culling rule; copy only needed geometry.
        distances = [clip['plane'].DistanceTo(p) for p in entry['cull_bounds'].GetCorners()]
        tol = doc.ModelAbsoluteTolerance
        limit = clip['depth'] if clip.get('elevation', True) else 0.0
        if max(distances) < -tol or (limit is not None and min(distances) > limit+tol):
            issues['outside_depth'] = issues.get('outside_depth', 0)+1
            return
        if not entry['prepared']:
            entry['geometry'] = world_geometry(geo, transform)
            entry['prepared'] = True
        geo = entry['geometry']
        if geo is None:
            issues['invalid'] = issues.get('invalid', 0)+1
            return
        record = dict(geometry=geo, source=source)
        records.append(record)  # Own the copy even if attribute resolution fails.
        if model_cache is not None:
            if 'bounds' not in entry: entry['bounds'] = geo.GetBoundingBox(True)
            record['bounds'] = entry['bounds']
        record['attributes'] = obj.Attributes.Duplicate()
        record['resolved'] = resolved_attributes(doc, obj.Attributes, parents)

    try:
        identity = G.Transform.Identity
        matrix = transform_values(identity) if model_cache is not None else None
        for obj in objects(doc):
            if obj.IsReference: continue
            # Unlisted instances can contain explicitly included nested members.
            walk(obj, identity, matrix, [], False, [], [])
        return records
    except:
        if model_cache is None:
            for record in records: record['geometry'].Dispose()
        raise


def drawing_metadata(doc, resolved, sources):
    return (json.dumps(sorted(set(sources))), doc.Layers[resolved.LayerIndex].FullPath,
            json.dumps(style_key(resolved)))


def drawing_attributes(doc, resolved, sources, role, metadata=None):
    a = resolved.Duplicate()
    metadata = metadata or drawing_metadata(doc, resolved, sources)
    a.SetUserString('ps:generator', OWNER)
    a.SetUserString('ps:role', role)
    a.SetUserString('ps:sources', metadata[0])
    a.SetUserString('ps:source_layer', metadata[1])
    a.SetUserString('ps:style', metadata[2])
    style = a.GetCustomSectionStyle()
    if role == 'section' and style is not None:
        if style.BoundaryColor.A: a.ObjectColor = style.BoundaryColor
        if style.BoundaryPrintColor.A: a.PlotColor = style.BoundaryPrintColor
        line = style.GetBoundaryLinetype()
        if line is not None: a.SetCustomLinetype(line)
    return a


def output(geo, attrs, role):
    return dict(geometry=geo, attributes=attrs, role=role)


def dispose_drawing_items(items, retained=()):
    """Release generated geometry replaced at a stage boundary; keep shared aliases."""
    keep = set(id(item['geometry']) for item in retained)
    for item in items:
        geometry = item['geometry']
        identity = id(geometry)
        if identity not in keep:
            keep.add(identity)
            geometry.Dispose()


def intersect(geo, plane, tol):
    """Intersect a prepared Brep or mesh after section candidate culling."""
    if isinstance(geo, G.Mesh):
        curves = [p.ToNurbsCurve() for p in G.Intersect.Intersection.MeshPlane(geo, None, plane, tol) or []]
    else:
        ok, curves, points = G.Intersect.Intersection.BrepPlane(geo, plane, tol)
        curves = list(curves or [])
    return list(G.Curve.JoinCurves(curves, tol) or [])


def planar_union(regions, plane, tol):
    if not regions:
        return []
    if len(regions) == 1:
        return regions
    # Disconnected regions already have final topology. Union only connected
    # bbox groups instead of rebuilding all regions in one global operation.
    tree = G.RTree()
    boxes = [b.GetBoundingBox(True) for b in regions]
    for i, box in enumerate(boxes): tree.Insert(box, i)
    pending = set(range(len(regions)))
    results = []
    try:
        for seed in range(len(regions)):
            if seed not in pending: continue
            group = [seed]
            pending.remove(seed)
            for i in group:
                box = G.BoundingBox(boxes[i].Min, boxes[i].Max)
                box.Inflate(tol)
                hits = []
                tree.Search(box, lambda sender, args: hits.append(args.Id))
                for j in sorted(hits):
                    if j in pending:
                        pending.remove(j)
                        group.append(j)
            if len(group) == 1:
                results.append(regions[group[0]])
                continue
            members = [regions[i] for i in group]
            # Coplanar inputs can require either orientation in Rhino 8.
            cut = G.Plane(plane)
            result = G.Brep.CreatePlanarUnion(members, cut, tol)
            if result is None or not len(result):
                cut.Flip()
                result = G.Brep.CreatePlanarUnion(members, cut, tol)
            if result is None or not len(result) or any(not b.IsValid for b in result):
                reason = next((str(b.IsValidWithLog()[1]).splitlines()[0]
                               for b in result or [] if not b.IsValid), 'No regions returned')
                raise ValueError('Planar union failed ({0} regions): {1}; no drawing was replaced'.format(
                    len(group), reason))
            results.extend(result)
        return results
    finally:
        tree.Dispose()


def clean_closed_curve(curve, plane, tol, angle_tol):
    # Ordinary simple loops need no Boolean reconstruction. Positive area is only
    # a fast-path guard; zero/uncertain area still uses the topology checks below.
    if curve.IsValid and curve.IsClosed and curve.IsInPlane(plane, tol):
        if not G.Intersect.Intersection.CurveSelf(curve, tol):
            area = G.AreaMassProperties.Compute(curve, tol)
            try:
                if area is not None and area.Area > area.AreaError:
                    return [curve], []
            finally:
                if area is not None: area.Dispose()
    # Resolve each loop independently; combining outer and inner loops fills holes.
    # Rhino can leave a sub-tolerance retrace unchanged at the first tolerance.
    fixed = None
    for accuracy in (tol, tol*.1):
        regions = G.Curve.CreateBooleanRegions([curve], plane, True, accuracy)
        if regions is None:
            fixed = None
            continue
        try:
            fixed = [c for i in range(regions.RegionCount) for c in regions.RegionCurves(i)]
        finally:
            regions.Dispose()
        if fixed and all(c.IsValid and c.IsClosed and not G.Intersect.Intersection.CurveSelf(c, tol)
                         for c in fixed):
            return fixed, []
    if fixed == []:
        ok, polyline = curve.TryGetPolyline()
        if ok:
            start = polyline[0]
            end = max(polyline, key=lambda p: start.DistanceTo(p))
            axis = G.Line(start,end)
            if axis.IsValid and all(axis.DistanceTo(p,False) <= R.RhinoMath.ZeroTolerance for p in polyline):
                return [], [curve]  # A closed linear retrace has no enclosed area.
        # Opposite-winding lobes can cancel algebraic area while enclosing regions.
        raise ValueError('Curve Boolean returned no region for a section boundary')
    if fixed:
        # Boolean can retain an exact out-and-back spur. Reuse the stroke split
        # so its area boundary and area-free linework are both preserved.
        pieces = [p for c in fixed for p in split_crossings(c, tol, angle_tol)[0]]
        closed = [p for p in pieces if p.IsClosed]
        if closed and all(not G.Intersect.Intersection.CurveSelf(p, tol) for p in pieces):
            return closed, [p for p in pieces if not p.IsClosed]
    raise ValueError('Cannot resolve self-crossing section boundary')


def region_boundaries(region, tol, angle_tol, cleanup_tol=None):
    # Use the union's 3D boundary edges. To3dCurve reconstructs trims and can
    # introduce tiny self-overlaps even when the Brep itself is valid.
    edges = region.DuplicateNakedEdgeCurves(True, True)
    curves = list(G.Curve.JoinCurves(edges, tol) or [])
    # A collapsed polyline with fewer than four points cannot bound an area.
    curves = [c for c in curves if not (isinstance(c, G.PolylineCurve)
              and not c.IsValid and c.PointCount < 4)]
    # Discard open join remnants shorter than the document tolerance; keep holes.
    curves = [c for c in curves if c.IsClosed or c.GetLength() > (cleanup_tol or tol)]
    cleaned = []
    for curve in curves:
        simplified = curve.Simplify(G.CurveSimplifyOptions.All, tol, angle_tol)
        if simplified and simplified.IsValid and simplified.IsClosed:
            curve = simplified
        # Clean each self-crossing loop separately so inner holes stay holes.
        if G.Intersect.Intersection.CurveSelf(curve, tol):
            ok, plane = region.Faces[0].TryGetPlane(tol)
            fixed = clean_closed_curve(curve, plane, tol, angle_tol)[0] if ok else []
            if not fixed:
                raise ValueError('Cannot resolve self-crossing section boundary')
            cleaned.extend(fixed)
        else:
            cleaned.append(curve)
    curves = cleaned
    if not curves or any(not c.IsValid or not c.IsClosed for c in curves):
        raise ValueError('Cannot extract closed boundaries from section union')
    return curves


def create_hatches(boundary, index, angle, scale, tol, region=None):
    # Native arc input can produce an invalid hatch plane; NURBS is exact.
    curves = [c.ToNurbsCurve() if isinstance(c, G.ArcCurve) else c for c in boundary]
    hatches = list(G.Hatch.Create(curves, index, angle, scale, tol) or [])
    if not hatches or any(not h.IsValid for h in hatches):
        hatches = list(G.Hatch.Create([c.ToNurbsCurve() for c in boundary], index, angle, scale, tol) or [])
    if region is not None and (not hatches or any(not h.IsValid for h in hatches)):
        # The union already owns valid face loops; rebuilding them from joined
        # edges can introduce self-crossings that Hatch.Create rejects.
        hatches = [G.Hatch.CreateFromBrep(region, face.FaceIndex, index, angle, scale,
                                       G.Point3d.Origin) for face in region.Faces]
        for hatch in hatches:
            if hatch is not None: hatch.PatternIndex = index  # Preserve system Solid (-1).
        if any(h is None for h in hatches): return []
    return hatches


def sections(doc, records, plane, hatch_on, progress=None):
    tol = section_tolerance(doc)
    groups = {}
    for record in records:
        original = record['geometry']
        if not meets_plane(record_bounds(record), plane, tol):
            continue
        # Select candidates before style grouping or mesh topology work.
        # Disjoint mesh pieces retain their own solid/fill classification.
        split = isinstance(original, G.Mesh) and original.DisjointMeshCount > 1
        pieces = original.SplitDisjointPieces() if split else [original]
        group = None
        try:
            for geo in pieces:
                if split and not meets_plane(geo.GetBoundingBox(True), plane, tol):
                    continue
                curves = intersect(geo, plane, tol)
                if not curves:
                    continue
                if group is None:
                    resolved = record.get('resolved') or resolved_attributes(doc, record['attributes'])
                    key = style_key(resolved)
                    group = groups.setdefault(key, dict(regions=[], fill=[], open=[], sources=[],
                                                         attrs=resolved, style=resolved.GetCustomSectionStyle()))
                    group['sources'].append(record['source'])
                if isinstance(geo, G.Brep) and geo.Faces.Count == 1 and not geo.IsSolid:
                    group['open'].extend(curves)  # A surface section is linework only.
                    continue
                closed = []
                for curve in curves:
                    if curve.IsClosed:
                        boundary, linework = clean_closed_curve(curve, plane, tol, doc.ModelAngleToleranceRadians)
                        closed.extend(boundary)
                        group['open'].extend(linework)
                    else:
                        group['open'].append(curve)
                regions = list(G.Brep.CreatePlanarBreps(closed, tol) or []) if closed else []
                if closed and not regions:
                    raise ValueError('Cannot create section regions: '+record['source'])
                group['regions'].extend(regions)
                if hatch_on and regions:
                    style = group['style']
                    if (style is not None and (style.HatchIndex != R.RhinoMath.UnsetIntIndex
                            or str(style.BackgroundFillMode) == 'SolidColor')
                            and (style.SectionFillRule == D.ObjectSectionFillRule.ClosedCurves or geo.IsSolid)):
                        group['fill'].extend(regions)
        finally:
            if split:
                for geo in pieces: geo.Dispose()
    results = []
    for key, group in sorted(groups.items()):
        layer = key[0]
        if progress: progress('union '+doc.Layers[layer].FullPath+' ('+str(len(group['regions']))+' regions)')
        regions = planar_union(group['regions'], plane, tol)
        boundaries = [region_boundaries(region, tol, doc.ModelAngleToleranceRadians,
                                       doc.ModelAbsoluteTolerance) for region in regions]
        curves = [piece for c in group['open']
                  for piece in split_crossings(c, tol, doc.ModelAngleToleranceRadians)[0]]
        for boundary in boundaries:
            curves.extend(boundary)
        metadata = drawing_metadata(doc, group['attrs'], group['sources'])
        attributes = drawing_attributes(doc, group['attrs'], group['sources'], 'section', metadata)
        for c in curves:
            results.append(output(c, attributes.Duplicate(), 'section'))
        if not hatch_on or not group['fill']:
            continue
        style = group['style']
        # Reuse the common union unless this style excludes open source objects.
        fill = regions
        if len(group['fill']) != len(group['regions']):
            fill = planar_union(group['fill'], plane, tol)
            boundaries = [region_boundaries(region, tol, doc.ModelAngleToleranceRadians,
                                           doc.ModelAbsoluteTolerance) for region in fill]
        if progress: progress('hatch '+doc.Layers[layer].FullPath)
        patterns = []
        if str(style.BackgroundFillMode) == 'SolidColor':
            patterns.append((hatch_pattern(doc, -1).Index, 0., 1.,
                             style.BackgroundFillColor))
        if style.HatchIndex != R.RhinoMath.UnsetIntIndex:
            pattern = hatch_pattern(doc, style.HatchIndex)
            patterns.append((pattern.Index, style.HatchRotationRadians, style.HatchScale,
                             style.HatchPatternColor))
        for region, boundary in zip(fill, boundaries):
            for index, angle, scale, color in patterns:
                hatches = create_hatches(boundary, index, angle, scale, tol, region)
                if not hatches or any(not h.IsValid for h in hatches):
                    reason = next((str(h.IsValidWithLog()[1]).splitlines()[0]
                                   for h in hatches if not h.IsValid), 'No hatch returned')
                    raise ValueError('Hatch creation failed on '+doc.Layers[layer].FullPath+': '+reason)
                for hatch in hatches:
                    direction = plane.XAxis*math.cos(angle)+plane.YAxis*math.sin(angle)
                    hatch.PatternRotation = math.atan2(direction*hatch.Plane.YAxis,
                                                        direction*hatch.Plane.XAxis)
                    hatch.BasePoint = plane.Origin
                    a = drawing_attributes(doc, group['attrs'], group['sources'], 'hatch', metadata)
                    if color.A:
                        a.ObjectColor, a.ColorSource = color, D.ObjectColorSource.ColorFromObject
                    else:
                        a.ObjectColor, a.ColorSource = group['attrs'].ObjectColor, D.ObjectColorSource.ColorFromObject
                    a.PlotColorSource = D.ObjectPlotColorSource.PlotColorFromLayer
                    results.append(output(hatch, a, 'hatch'))
    return results


def elevations(doc, records, plane, depth, near_width, far_width, near_dark, far_dark, profile=None):
    tol = doc.ModelAbsoluteTolerance
    if depth == 0:
        return []
    candidates = []
    for record in records:
        distances = [plane.DistanceTo(p) for p in record_bounds(record).GetCorners()]
        if max(distances) < -tol or (depth is not None and min(distances) > depth+tol):
            continue
        candidates.append(record)
    if not candidates:
        return []
    parameters = G.HiddenLineDrawingParameters()
    parameters.AbsoluteTolerance = tol
    parameters.Flatten = True
    parameters.IncludeHiddenCurves = False
    parameters.IncludeTangentEdges = True
    parameters.IncludeTangentSeams = False
    parameters.OccludingSectionOption = True
    viewport = R.Display.RhinoViewport()
    hld = None
    try:
        viewport.ChangeToParallelProjection(True)
        # Rhino clipping normal points INTO the visible model; HLD clips its positive side.
        viewport.SetCameraDirection(plane.Normal, True)
        viewport.CameraUp = plane.YAxis
        viewport.SetCameraLocation(plane.Origin-plane.Normal, False)
        viewport.SetCameraTarget(plane.Origin, False)
        parameters.SetViewport(viewport)
        front = G.Plane(plane); front.Flip()
        parameters.AddClippingPlane(front)
        if depth is not None:
            back = G.Plane(plane)
            back.Origin = plane.Origin+plane.Normal*depth
            parameters.AddClippingPlane(back)
        for i, record in enumerate(candidates):
            if not parameters.AddGeometry(record['geometry'], i):
                raise ValueError('HLD rejected geometry: '+record['source'])
        watch = System.Diagnostics.Stopwatch.StartNew() if profile is not None else None
        hld = G.HiddenLineDrawing.Compute(parameters, True)
        if watch is not None:
            profile['hld_compute_seconds'] = watch.Elapsed.TotalSeconds
        if hld is None:
            raise ValueError('HiddenLineDrawing failed')
        if watch is not None: watch.Restart()
        hld.RejoinCompatibleVisible()
        if watch is not None:
            profile['hld_rejoin_seconds'] = watch.Elapsed.TotalSeconds
            watch.Restart()
        ok, inverse = hld.WorldToHiddenLine.TryGetInverse()
        if not ok:
            raise ValueError('Invalid HLD coordinate transform')
        restore = G.Transform.PlanarProjection(plane)*inverse
        visible, distances = [], {}
        for segment in hld.Segments:
            parent = segment.ParentCurve
            if segment.SegmentVisibility != G.HiddenLineDrawingSegment.Visibility.Visible:
                continue
            if parent.SourceObject is None or str(parent.SilhouetteType) == 'SectionCut':
                continue
            index = int(parent.SourceObject.Tag)
            curve = segment.CurveGeometry.DuplicateCurve()
            if not curve.Transform(restore) or curve.IsShort(R.RhinoMath.ZeroTolerance):
                curve.Dispose()
                continue
            if index not in distances:
                # Styling uses one bbox depth per visible source, not per segment.
                distances[index] = max(0.0, plane.DistanceTo(record_bounds(candidates[index]).Center))
            visible.append((distances[index], index, curve))
        if not visible:
            return []
        near, far = min(x[0] for x in visible), max(x[0] for x in visible)
        result, attributes = [], {}
        for distance, index, curve in sorted(visible, key=lambda x: x[0]):
            if index not in attributes:
                source = candidates[index]
                width, gray = relative_style(distance, near, far, near_width, far_width, near_dark, far_dark)
                resolved = source.get('resolved') or resolved_attributes(doc, source['attributes'])
                a = drawing_attributes(doc, resolved, [source['source']], 'elevation')
                a.PlotWeight, a.PlotWeightSource = width, D.ObjectPlotWeightSource.PlotWeightFromObject
                a.PlotColor = Color.FromArgb(gray, gray, gray)
                a.PlotColorSource = D.ObjectPlotColorSource.PlotColorFromObject
                a.SetUserString('ps:depth', str(distance))
                attributes[index] = a
            result.append(output(curve, attributes[index].Duplicate(), 'elevation'))
        if watch is not None:
            profile['hld_output_seconds'] = watch.Elapsed.TotalSeconds
        return result
    finally:
        if hld is not None: hld.Dispose()
        viewport.Dispose()


def deduplicate(items, tol, section_tol=None):
    """Keep sections first; elevation overlap uses the document's cleanup tolerance."""
    trees, kept, result = {}, {}, []
    try:
        for item in items:
            curve = item['geometry']
            if not isinstance(curve, G.Curve):
                result.append(item)
                continue
            layer = (item['attributes'].LayerIndex, item['attributes'].GetUserString('ps:style'))
            if layer not in trees:
                trees[layer], kept[layer] = G.RTree(), []
            item_tol = section_tol if item['role']=='section' and section_tol is not None else tol
            box = curve.GetBoundingBox(True); box.Inflate(item_tol)
            hits = []
            trees[layer].Search(box, lambda sender, args: hits.append(args.Id))
            intervals = []
            for index in hits:
                events = G.Intersect.Intersection.CurveCurve(curve, kept[layer][index], item_tol, item_tol)
                intervals.extend((event.OverlapA.T0, event.OverlapA.T1) for event in events or [] if event.IsOverlap)
            cursor, end = curve.Domain.T0, curve.Domain.T1
            pieces = []
            for start, stop in sorted(intervals):
                start, stop = max(cursor, start), min(end, stop)
                if stop <= cursor: continue
                if start > cursor: pieces.append(curve.Trim(cursor, start))
                cursor = max(cursor, stop)
            if cursor < end:
                pieces.append(curve if cursor == curve.Domain.T0 else curve.Trim(cursor, end))
            for piece in pieces:
                minimum = R.RhinoMath.ZeroTolerance if item['role']=='elevation' else item_tol
                if piece is None or piece.IsShort(minimum):
                    continue
                entry = dict(item); entry['geometry'] = piece
                result.append(entry)
                trees[layer].Insert(piece.GetBoundingBox(True), len(kept[layer]))
                kept[layer].append(piece)
        return result
    finally:
        for tree in trees.values(): tree.Dispose()


def repair_invalid_polyline(curve):
    if curve.IsValid or not isinstance(curve, G.PolylineCurve): return curve
    # Native Split/projection can produce invalid A-B-A strokes. The return edge
    # duplicates the same visible segment; keep it once without approximating.
    if curve.PointCount == 3 and curve.Point(0) == curve.Point(2):
        return G.LineCurve(curve.Point(0), curve.Point(1))
    # Projection can collapse consecutive vertices. Use numerical tolerance so
    # valid small details survive independently of the document tolerance.
    simplified = curve.Simplify(G.CurveSimplifyOptions.All, R.RhinoMath.ZeroTolerance,
                               R.RhinoMath.ZeroTolerance)
    if simplified is not None:
        if simplified.IsValid: return simplified
        simplified.Dispose()
    return curve


def split_crossings(curve, tol, angle_tol):
    # Split strokes without turning an open section or elevation into a filled area.
    events = G.Intersect.Intersection.CurveSelf(curve, tol)
    parameters = []
    for event in events or []:
        parameters.extend([event.ParameterA, event.ParameterB] if event.IsPoint else
                          [event.OverlapA.T0, event.OverlapA.T1, event.OverlapB.T0, event.OverlapB.T1])
    start, end = curve.Domain.T0, curve.Domain.T1
    at_seam = curve.IsClosed and any(t in (start,end) for t in parameters)
    parameters = sorted(set(t for t in parameters if start<t<end))
    if at_seam:
        # Split requires interior parameters and rejoins across a closed seam.
        # Trim each interval so loops meeting at the seam remain separate.
        cuts = [start]+parameters+[end]
        pieces = [curve.Trim(a,b) for a,b in zip(cuts,cuts[1:])]
        if any(piece is None for piece in pieces):
            raise ValueError('Curve trim failed at closed self-intersection seam')
    else:
        pieces = list(curve.Split(parameters) or []) if parameters else [curve]
    for index, piece in enumerate(pieces):
        if not piece.IsClosed and piece.PointAtStart.DistanceTo(piece.PointAtEnd)<=tol:
            piece.MakeClosed(tol)
        pieces[index] = piece = repair_invalid_polyline(piece)
        if parameters:
            simplified = piece.Simplify(G.CurveSimplifyOptions.All,tol,angle_tol)
            if simplified is not None and simplified.IsValid: pieces[index] = simplified
    if not pieces or any(not c.IsValid for c in pieces):
        reason = '; '.join('{0:g}: {1}'.format(c.GetLength(),c.IsValidWithLog()[1]) for c in pieces if not c.IsValid)
        raise ValueError('Invalid curve after self-intersection split: '+reason)
    return pieces, bool(parameters), any(event.IsOverlap for event in events or [])


def cleanup_elevations(doc, items, plane=G.Plane.WorldXY, small_details=True):
    """Join equal styles; optionally omit small details without cutting long contours."""
    mm = R.RhinoMath.UnitScale(R.UnitSystem.Millimeters, doc.ModelUnitSystem)
    tol, cutoff = doc.ModelAbsoluteTolerance, 20.*mm
    groups, result = {}, [i for i in items if i['role']!='elevation']
    for item in items:
        if item['role']=='elevation':
            groups.setdefault(style_key(item['attributes']), []).append(item)
    report = dict(mode='Keep' if small_details else 'Omit',
                  input=sum(len(g) for g in groups.values()), joined=0, repaired_join=0, self_split=0, join_discarded=0,
                  removed_small=0, protected_small=0)
    if not groups: return items, report
    for group in groups.values():
        mapping = clr.Reference[System.Array[System.Int32]]()
        curves = list(G.Curve.JoinCurves([i['geometry'] for i in group], tol, False, mapping) or [])
        if mapping.Value is None or len(mapping.Value)!=len(group):
            raise ValueError('Elevation join failed; previous drawing retained')
        contributors = [[] for c in curves]
        for i, k in enumerate(mapping.Value):
            if 0<=k<len(curves): contributors[k].append(group[i])
            elif group[i]['geometry'].GetBoundingBox(plane).Diagonal.Length<=tol:
                report['join_discarded'] += 1  # Native Join can discard sub-tolerance remnants.
            else:
                raise ValueError('Elevation join lost a curve larger than document tolerance')
        report['joined'] += len(curves)
        for curve, members in zip(curves, contributors):
            if curve.GetBoundingBox(plane).Diagonal.Length <= tol:
                report['removed_small'] += 1
                continue
            if not curve.IsValid:
                # Reuse exact retrace/duplicate-vertex repair before the existing
                # document-tolerance simplification of a native Join result.
                simplified = repair_invalid_polyline(curve)
                if not simplified.IsValid:
                    simplified = curve.Simplify(G.CurveSimplifyOptions.All,tol,doc.ModelAngleToleranceRadians)
                if simplified is None or not simplified.IsValid:
                    raise ValueError('Invalid elevation join: '+str(curve.IsValidWithLog()[1]))
                curve = simplified
                report['repaired_join'] += 1
            if not curve.IsClosed and curve.PointAtStart.DistanceTo(curve.PointAtEnd)<=tol:
                curve.MakeClosed(tol)  # Only close the numerical seam, not missing edges.
            attrs = members[0]['attributes'].Duplicate()
            sources = set(s for i in members for s in json.loads(i['attributes'].GetUserString('ps:sources') or '[]'))
            attrs.SetUserString('ps:sources', json.dumps(sorted(sources)))
            depths = set(i['attributes'].GetUserString('ps:depth') for i in members)
            if len(depths)>1: attrs.DeleteUserString('ps:depth')
            try:
                pieces, split, overlaps = split_crossings(curve, tol, doc.ModelAngleToleranceRadians)
            except ValueError as error:
                raise ValueError(str(error)+' on '+str(attrs.GetUserString('ps:source_layer')))
            if split: report['self_split'] += 1
            entries = [output(c, attrs.Duplicate(), 'elevation') for c in pieces]
            if overlaps: entries = deduplicate(entries,tol)
            result.extend(entries)
    # Different styles cannot share one curve. Preserve endpoint bridges in Omit;
    # Keep retains valid details regardless of size or contact with other curves.
    boxes = {i: item['geometry'].GetBoundingBox(plane) for i,item in enumerate(result)
             if isinstance(item['geometry'], G.Curve)}
    pending = set(i for i,box in boxes.items() if result[i]['role']=='elevation' and box.Diagonal.Length<=cutoff)
    small = set(pending)
    if not pending: return result, report
    remove = set(i for i in small if boxes[i].Diagonal.Length<=tol)
    if small_details:
        report['removed_small'] += len(remove)
        report['protected_small'] = len(small)-len(remove)
        return [item for i,item in enumerate(result) if i not in remove], report
    # A closed small outline is already complete, not a member needed by Join.
    remove.update(i for i in small if result[i]['geometry'].IsClosed)
    pending.difference_update(remove)
    tree = G.RTree()
    try:
        for i in boxes:
            if i not in remove: tree.Insert(result[i]['geometry'].GetBoundingBox(True), i)
        for seed in sorted(pending):
            if seed not in pending: continue
            group = [seed]; pending.remove(seed)
            bounds, anchors = G.BoundingBox.Empty, G.BoundingBox.Empty
            for i in group:
                bounds.Union(boxes[i])
                curve = result[i]['geometry']
                box = curve.GetBoundingBox(True); box.Inflate(tol)
                hits = []
                tree.Search(box, lambda sender,args: hits.append(args.Id))
                for j in hits:
                    if j==i or (j in small and j not in pending): continue
                    other = result[j]['geometry']
                    contacts = []
                    if not other.IsClosed:
                        for point in (curve.PointAtStart,curve.PointAtEnd):
                            if min(point.DistanceTo(other.PointAtStart),point.DistanceTo(other.PointAtEnd))<=tol:
                                contacts.append(point)
                    if not contacts: continue
                    if j in pending:
                        pending.remove(j); group.append(j)
                    elif j not in small:
                        for point in contacts: anchors.Union(point)
            anchored = anchors.IsValid and anchors.Diagonal.Length>tol
            if not anchored and bounds.Diagonal.Length<=cutoff: remove.update(group)
        report['removed_small'] += len(remove)
        report['protected_small'] = len(small)-len(remove)
        return [item for i,item in enumerate(result) if i not in remove], report
    finally:
        tree.Dispose()


def generate(doc, cp, hatch=True, elevation=True, target=None,
             near_width=.09, far_width=.04, near_dark=80., far_dark=45., progress=None, place=True,
             small_details=True, profile=None, model_cache=None):
    validate_options(near_width, far_width, near_dark, far_dark)
    clip = read_clip(doc, cp, target)
    clip['elevation'] = elevation
    issues = {}
    if progress: progress('parse')
    records = model_objects(doc, clip, issues, model_cache)
    items = []
    try:
        fallbacks = sorted(set((doc.Layers[r['attributes'].LayerIndex].FullPath,
                                r['resolved'].GetUserString('ps:hatch_fallback')) for r in records
                               if r['resolved'].GetUserString('ps:hatch_fallback')))
        if fallbacks:
            issues['hatch_fallback'] = ['{0}: pattern {1} -> Solid'.format(*row) for row in fallbacks]
            if progress:
                for warning in issues['hatch_fallback']: progress('WARNING '+warning)
        if progress: progress('section ('+str(len(records))+' objects)')
        items = sections(doc, records, clip['plane'], hatch, progress)
        if elevation:
            if progress: progress('elevation')
            items.extend(elevations(doc, records, clip['plane'], clip['depth'],
                                    near_width, far_width, near_dark, far_dark, profile))
        if progress: progress('overlaps')
        previous, items = items, deduplicate(items, doc.ModelAbsoluteTolerance, section_tolerance(doc))
        dispose_drawing_items(previous, items)
        if progress: progress('join / small elevation outlines (20 mm)')
        previous = items
        items, cleanup = cleanup_elevations(doc, items, clip['plane'], small_details)
        dispose_drawing_items(previous, items)
        if place:
            move_drawing(dict(objects=items), clip['plane'], clip['target'])
        for item in items:
            item['attributes'].Name = cp.Name
            item['attributes'].SetUserString('ps:clip', str(cp.Id))
        report = dict(sources=len(records), skipped=issues, cleanup=cleanup,
                      section=sum(i['role']=='section' for i in items),
                      hatch=sum(i['role']=='hatch' for i in items),
                      elevation=sum(i['role']=='elevation' for i in items))
        drawing = dict(objects=items, report=report)
        items = []  # The caller now owns the final drawing geometry.
        return drawing
    finally:
        dispose_drawing_items(items)
        if model_cache is None:
            for record in records: record['geometry'].Dispose()


def drawing_objects(doc, cp):
    index = doc.Layers.FindByFullPath('Drawing', -1)
    text = doc.Layers[index].GetUserString('ps:clip:'+str(cp.Id)) if index >= 0 else None
    ids = set(System.Guid(value) for value in json.loads(text or '[]'))
    return [o for o in objects(doc) if not o.IsReference and (o.Id in ids
            or (o.Attributes.GetUserString('ps:generator') == OWNER
                and o.Attributes.GetUserString('ps:clip') == str(cp.Id)))]


def saved_placement(cp, existing):
    saved = set(o.Attributes.GetUserString('ps:placement') for o in existing)
    if len(saved) > 1: raise ValueError('Drawing has inconsistent placement metadata; regenerate it first')
    return draft_plane((next(iter(saved)) if saved else None) or cp.Attributes.GetUserString('draft_plane'))


def output_attributes(original):
    attrs = original.Duplicate()
    values = [(key, attrs.GetUserString(key)) for key in ('ps:source_layer', 'ps:placement')]
    attrs.DeleteAllUserStrings()
    for key, value in values:
        if value is not None: attrs.SetUserString(key, value)
    return attrs


def save_drawing_registry(doc, cp, value):
    index = local_output_layer(doc, 'Drawing')
    layer = doc.Layers[index]
    layer.EnsurePrivateCopy()  # Keep the pre-edit layer available to native Undo.
    key = 'ps:clip:'+str(cp.Id)
    previous = layer.GetUserString(key)
    if not layer.SetUserString(key, value): raise ValueError('Cannot set drawing ownership')
    if not doc.Layers.Modify(layer, index, True):
        raise ValueError('Cannot save drawing ownership on Drawing layer')
    return previous


def output_layer(role):
    return {'elevation': ELEVATION_LAYER, 'hatch': HATCH_LAYER}.get(role, SECTION_LAYER)


def local_output_layer(doc, path):
    for end in range(1, len(path.split('::'))+1):
        name = '::'.join(path.split('::')[:end])
        index = doc.Layers.FindByFullPath(name, -1)
        if index >= 0:
            layer = doc.Layers[index]
            if layer.IsReference or layer.IsLocked or not layer.IsVisible:
                raise ValueError('Output layer must be local, visible and unlocked: '+name)
    index = doc.Layers.AddPath(path)
    if index < 0: raise ValueError('Cannot create output layer: '+path)
    return index


def bake(doc, cp, drawing, target=None):
    old = drawing_objects(doc, cp)
    layers = {role: local_output_layer(doc, output_layer(role))
              for role in set(i['role'] for i in drawing['objects'])}
    added, removed = [], []
    original = cp.Attributes.Duplicate()
    original_registry = None
    registry_changed = False
    try:
        for item in drawing['objects']:
            attrs = output_attributes(item['attributes'])
            attrs.LayerIndex = layers[item['role']]
            style = attrs.GetCustomSectionStyle()
            geometry = item['geometry']
            # A document without Solid can compute with the system pattern (-1).
            # Materialize it only when output is actually added to that document.
            if (style is not None and style.HatchIndex == -1) or (item['role']=='hatch' and geometry.PatternIndex == -1):
                solid = doc.HatchPatterns.FindName('Solid')
                index = solid.Index if solid else doc.HatchPatterns.Add(D.HatchPattern.Defaults.Solid)
                if index < 0: raise ValueError('Cannot add Solid hatch pattern')
                if style is not None and style.HatchIndex == -1:
                    style.HatchIndex = index
                    attrs.SetCustomSectionStyle(style)
                if item['role']=='hatch' and geometry.PatternIndex == -1:
                    geometry = geometry.Duplicate()
                    geometry.PatternIndex = index
            try:
                guid = doc.Objects.Add(geometry, attrs)
            finally:
                if geometry is not item['geometry']: geometry.Dispose()
            if guid == System.Guid.Empty:
                raise ValueError('Failed to add drawing object')
            added.append(guid)
        if target is not None and not cp.IsReference:
            attrs = original.Duplicate()
            attrs.SetUserString('draft_plane', plane_json(target))
            if not doc.Objects.ModifyAttributes(cp.Id, attrs, True):
                raise ValueError('Failed to save draft_plane')
        original_registry = save_drawing_registry(doc, cp, json.dumps([str(i) for i in added]))
        registry_changed = True
        for obj in old:
            serial = obj.RuntimeSerialNumber
            if not doc.Objects.Delete(obj, True, True):
                raise ValueError('Cannot remove previous drawing object '+str(obj.Id))
            removed.append(serial)
        return added
    except Exception:
        for serial in removed: doc.Objects.Undelete(serial)
        for guid in added: doc.Objects.Delete(doc.Objects.FindId(guid), True, True)
        if registry_changed: save_drawing_registry(doc, cp, original_registry)
        if target is not None and not cp.IsReference: doc.Objects.ModifyAttributes(cp.Id, original, True)
        raise


def placement_plane(cut, point):
    target = G.Plane(G.Plane.WorldXY)
    target.Origin = G.Point3d(point.X, point.Y, 0)
    return target


def drawing_transform(source, target):
    target = placement_plane(source, target.Origin)
    # Applied right to left: align, mirror, then clear residual output Z.
    return (G.Transform.PlanarProjection(G.Plane.WorldXY)
            * G.Transform.Mirror(target.Origin, G.Vector3d.YAxis)
            * G.Transform.PlaneToPlane(source, target))


def drawing_frame(drawing, plane):
    bounds = G.BoundingBox.Empty
    for item in drawing['objects']:
        bounds.Union(item['geometry'].GetBoundingBox(plane))
    return G.Rectangle3d(plane, G.Interval(bounds.Min.X, bounds.Max.X),
                         G.Interval(bounds.Min.Y, bounds.Max.Y))


def pick_placement(drawing, cut, name, origin=None):
    rectangle = drawing_frame(drawing, cut)
    getter = R.Input.Custom.GetPoint()
    getter.SetCommandPrompt('Place clipping plane origin: '+name)
    def preview(sender, event):
        target = placement_plane(cut, event.CurrentPoint)
        transform = (G.Transform.Translation(target.Origin-origin) if origin is not None
                     else drawing_transform(cut, target))
        corners = [transform*rectangle.Corner(i) for i in range(4)]
        event.Display.DrawPolyline(corners+[corners[0]], Color.DodgerBlue, 2)
        event.Display.DrawDot(target.Origin, 'Clipping origin', Color.DodgerBlue, Color.White)
    getter.DynamicDraw += preview
    try:
        if getter.Get() != R.Input.GetResult.Point: return None
        return placement_plane(cut, getter.Point())
    finally:
        getter.DynamicDraw -= preview
        getter.Dispose()


def move_drawing(drawing, source, target):
    transform = drawing_transform(source, target)
    for item in drawing['objects']:
        transformed = item['geometry'].Transform(transform)
        curve = item['geometry']
        if transformed and isinstance(curve,G.Curve):
            item['geometry'] = repair_invalid_polyline(curve)
            if item['geometry'] is not curve: curve.Dispose()
        if not transformed or not item['geometry'].IsValid:
            valid, reason = item['geometry'].IsValidWithLog()
            raise ValueError('Invalid '+item['role']+' output: '+str(reason)+'; previous drawing retained')
        item['attributes'].SetUserString('ps:placement', plane_json(placement_plane(source, target.Origin)))


def reposition_drawing(doc, cp, target=None):
    """Translate existing XY output in place; retain IDs and user edits."""
    existing = drawing_objects(doc, cp)
    if not existing: raise ValueError('No generated drawing to move')
    origin = saved_placement(cp, existing).Origin
    origin = G.Point3d(origin.X, origin.Y, 0)
    drawing = dict(objects=[output(o.Geometry, o.Attributes, o.Attributes.GetUserString('ps:role')) for o in existing])
    if target is None: target = pick_placement(drawing, G.Plane.WorldXY, cp.Name or str(cp.Id), origin)
    if target is None: return False
    target = placement_plane(G.Plane.WorldXY, target.Origin)
    transform = G.Transform.Translation(target.Origin-origin)
    original_cp = cp.Attributes.Duplicate()
    prepared, changed = [], []
    try:
        for obj in existing:
            before, after = obj.Geometry.Duplicate(), obj.Geometry.Duplicate()
            prepared.append((obj.Id, before, obj.Attributes.Duplicate(), after))
            if not after.Transform(transform) or not after.IsValid:
                raise ValueError('Invalid drawing geometry after move')
        for guid, before, attrs_before, after in prepared:
            if not doc.Objects.Replace(guid, after, True): raise ValueError('Cannot move drawing object '+str(guid))
            changed.append((guid, before, attrs_before))
            # Rhino 8 can ignore user-text edits copied before Replace.
            attrs = output_attributes(doc.Objects.FindId(guid).Attributes)
            attrs.SetUserString('ps:placement', plane_json(target))
            if not doc.Objects.ModifyAttributes(guid, attrs, True): raise ValueError('Cannot update drawing placement')
        if not cp.IsReference:
            attrs = original_cp.Duplicate()
            attrs.SetUserString('draft_plane', plane_json(target))
            if not doc.Objects.ModifyAttributes(cp.Id, attrs, True): raise ValueError('Cannot save draft_plane')
        save_drawing_registry(doc, cp, json.dumps([str(o.Id) for o in existing]))
        return True
    except Exception:
        restored = []
        for guid, geo, attrs in reversed(changed):
            replaced = doc.Objects.Replace(guid, geo, True)
            current = doc.Objects.FindId(guid).Attributes.Duplicate()
            current.DeleteAllUserStrings()
            for key in attrs.GetUserStrings().AllKeys: current.SetUserString(key, attrs.GetUserString(key))
            restored.append(doc.Objects.ModifyAttributes(guid, current, True) and replaced)
        if not cp.IsReference: restored.append(doc.Objects.ModifyAttributes(cp.Id, original_cp, True))
        if not all(restored): raise ValueError('Move failed and rollback was incomplete; use Undo')
        raise
    finally:
        for guid, before, attrs_before, after in prepared:
            before.Dispose(); after.Dispose()


def export_path(folder, name, extension):
    invalid = set(System.IO.Path.GetInvalidFileNameChars())
    stem = ''.join('_' if c in invalid else c for c in name).strip(' .')[:120] or 'Section'
    reserved = ['CON','PRN','AUX','NUL']+['COM'+str(i) for i in range(1,10)]+['LPT'+str(i) for i in range(1,10)]
    if stem.split('.')[0].upper() in reserved: stem = '_'+stem
    path, number = os.path.join(folder, stem+extension), 2
    while os.path.exists(path):
        path = os.path.join(folder, stem+'_'+str(number)+extension)
        number += 1
    return path


def export_drawing(doc, drawing, folder, name):
    """Write drawing only; table indices belong to the destination 3dm."""
    model = R.FileIO.File3dm()
    temporary = os.path.join(folder, str(System.Guid.NewGuid())+'.tmp.3dm')
    try:
        for key in ('ModelUnitSystem', 'ModelAbsoluteTolerance',
                    'ModelAngleToleranceRadians', 'ModelRelativeTolerance'):
            setattr(model.Settings, key, getattr(doc, key))
        patterns, linetypes, layers = {}, {}, {}
        def pattern(index):
            if index not in patterns:
                original = hatch_pattern(doc, index)
                model.HatchPatterns.Add(original)
                patterns[index] = model.HatchPatterns.FindId(original.Id).Index
            return patterns[index]
        def linetype(index):
            if index < 0: return index  # Rhino built-in linetypes use negative indices.
            if index not in linetypes:
                original = doc.Linetypes[index]
                model.Linetypes.Add(original)
                linetypes[index] = model.Linetypes.FindId(original.Id).Index
            return linetypes[index]
        def layer(path):
            if path in layers: return layers[path]
            parent = System.Guid.Empty
            for end, part in enumerate(path.split('::'), 1):
                found = model.Layers.FindName(part, parent)
                if found is None:
                    copied = D.Layer()
                    copied.Name, copied.ParentLayerId = part, parent
                    # Preserve local drawing-layer print settings (hatches are ByLayer).
                    index = doc.Layers.FindByFullPath('::'.join(path.split('::')[:end]), -1)
                    if index >= 0 and not doc.Layers[index].IsReference:
                        original = doc.Layers[index]
                        copied.Color, copied.PlotColor, copied.PlotWeight = original.Color, original.PlotColor, original.PlotWeight
                    model.Layers.Add(copied)
                    found = model.Layers.FindName(part, parent)
                parent = found.Id
            layers[path] = found.Index
            return found.Index
        for item in drawing['objects']:
            attrs = output_attributes(item['attributes'])
            attrs.LayerIndex = layer(output_layer(item['role']))
            attrs.LinetypeIndex = linetype(attrs.LinetypeIndex)
            style = attrs.GetCustomSectionStyle()
            if style is not None and style.HatchIndex != R.RhinoMath.UnsetIntIndex:
                style.HatchIndex = pattern(style.HatchIndex)
                attrs.SetCustomSectionStyle(style)
            attrs.MaterialIndex = -1
            geometry = item['geometry'].Duplicate()
            try:
                if item['role']=='hatch': geometry.PatternIndex = pattern(geometry.PatternIndex)
                if model.Objects.Add(geometry, attrs) == System.Guid.Empty:
                    raise ValueError('Failed to add drawing to export')
            finally:
                geometry.Dispose()
        path = export_path(folder, name, '.3dm')
        if not model.Write(temporary, 8): raise IOError('3dm export failed')
        System.IO.File.Move(temporary, path)  # Does not overwrite an existing file.
        return path
    finally:
        model.Dispose()
        if os.path.exists(temporary): os.remove(temporary)


def pdf_settings(cp):
    """Clipping user text: paper width*height in mm and the 1:N denominator."""
    try:
        paper = [float(v) for v in (cp.Attributes.GetUserString('Paper') or '210*297').split('*')]
        if len(paper) != 2 or any(not finite(v) or v <= 0 for v in paper): raise ValueError()
    except ValueError:
        raise ValueError('Paper must be positive width*height in mm, e.g. 210*297')
    try:
        scale = float(cp.Attributes.GetUserString('Scale') or '300')
        if not finite(scale) or scale <= 0: raise ValueError()
    except ValueError:
        raise ValueError('Scale must be a positive denominator, e.g. 300 for 1:300')
    return paper, scale


def export_pdf(doc, drawing, folder, name, paper, scale):
    """Print an XY drawing centered at zero; never bake into the source doc."""
    import tempfile
    import shutil
    from System.Drawing import Size, Rectangle
    if str(doc.ModelUnitSystem) in ('None', 'Unset', 'CustomUnits'):
        raise ValueError('PDF requires a standard model unit system')
    units = R.RhinoMath.UnitScale(R.UnitSystem.Millimeters, doc.ModelUnitSystem)
    half_w, half_h = [v*scale*units/2. for v in paper]
    kept = []
    for item in drawing['objects']:
        bounds = item['geometry'].GetBoundingBox(True)
        pad = max(.18, item['attributes'].PlotWeight)*scale*units
        if (bounds.Max.X < -half_w-pad or bounds.Min.X > half_w+pad or
                bounds.Max.Y < -half_h-pad or bounds.Min.Y > half_h+pad): continue
        attrs = item['attributes'].Duplicate()
        attrs.DeleteAllUserStrings()  # Provenance is large and has no printed content.
        kept.append(output(item['geometry'], attrs, item['role']))
    if not kept: raise ValueError('No drawing geometry inside the PDF paper window')
    work = tempfile.mkdtemp(prefix='PlanSection-pdf-')
    temporary = os.path.join(folder, str(System.Guid.NewGuid())+'.tmp.pdf')
    target, viewport, settings = None, None, None
    try:
        path3dm = export_drawing(doc, dict(objects=kept), work, 'drawing')
        target = R.RhinoDoc.OpenHeadless(path3dm)
        if target is None: raise ValueError('Cannot open temporary PDF drawing')
        viewport = R.Display.RhinoViewport()
        # Native capture clamps strokes to one dot. Keep even the thinnest print
        # width; vector output does not allocate a page-sized bitmap.
        dot_mm = min([.01]+[i['attributes'].PlotWeight for i in kept if i['attributes'].PlotWeight > 0])
        size = Size(int(round(paper[0]/dot_mm)), int(round(paper[1]/dot_mm)))
        if size.Width <= 0 or size.Height <= 0: raise ValueError('PDF paper is too small')
        viewport.Size = size
        viewport.SetProjection(R.Display.DefinedViewportProjection.Top, 'PlanSection PDF', False)
        distance = max(half_w, half_h)*4
        viewport.SetCameraLocations(G.Point3d.Origin, G.Point3d(0,0,distance))
        info = D.ViewportInfo(viewport)
        if not info.SetFrustum(-half_w,half_w,-half_h,half_h,distance/100.,distance*2):
            raise ValueError('Invalid PDF paper/scale extent')
        if not viewport.SetViewProjection(info, False): raise ValueError('Cannot set PDF viewport')
        settings = R.Display.ViewCaptureSettings()
        settings.Document = target
        settings.SetViewport(viewport)
        settings.Resolution = 25.4/dot_mm
        settings.SetLayout(size, Rectangle(0,0,size.Width,size.Height))
        settings.SetModelScaleToValue(scale)
        settings.RasterMode = False
        settings.OutputColor = R.Display.ViewCaptureSettings.ColorMode.PrintColor
        settings.UsePrintWidths = True
        settings.DefaultPrintWidthMillimeters = .18
        settings.DrawBackground = settings.DrawGrid = settings.DrawAxis = False
        settings.DrawClippingPlanes = settings.DrawMargins = False
        settings.HeaderText = settings.FooterText = ''
        if not settings.IsValid: raise ValueError('Invalid PDF capture settings')
        pdf = R.FileIO.FilePdf.Create()
        if pdf is None or pdf.AddPage(settings) < 0: raise ValueError('Rhino PDF page creation failed')
        pdf.Write(temporary)
        if not os.path.isfile(temporary) or os.path.getsize(temporary) == 0:
            raise IOError('Rhino PDF export failed')
        path = export_path(folder, name, '.pdf')
        System.IO.File.Move(temporary, path)
        return path
    finally:
        if settings is not None: settings.Dispose()
        if viewport is not None: viewport.Dispose()
        if target is not None: target.Dispose()
        shutil.rmtree(work)
        if os.path.exists(temporary): os.remove(temporary)


def clipping_dialog(labels):
    import Eto.Forms as F
    import Eto.Drawing as E
    import scriptcontext as sc
    dialog = F.Dialog()
    dialog.Title, dialog.Resizable = 'PlanSection', True
    dialog.ClientSize = E.Size(*sc.sticky.get('PlanSection:list_size', (900, 600)))
    dialog.MinimumSize, dialog.Padding = E.Size(500, 300), E.Padding(12)
    grid = F.GridView()
    grid.AllowMultipleSelection, grid.ShowHeader = True, False
    column = F.GridColumn()
    column.DataCell, column.Expand = F.TextBoxCell(0), True
    grid.Columns.Add(column)
    grid.DataStore = [[label] for label in labels]
    ok, cancel = F.Button(), F.Button()
    ok.Text, cancel.Text = 'OK', 'Cancel'
    def accept(sender, event):
        selected = sorted(grid.SelectedRows)
        if selected:
            dialog.Tag = selected
            dialog.Close()
    def keydown(sender, event):
        if event.Key == F.Keys.Enter:
            event.Handled = True
            accept(sender, event)
    def remember(sender, event):
        sc.sticky['PlanSection:list_size'] = (dialog.ClientSize.Width, dialog.ClientSize.Height)
    ok.Click += accept
    cancel.Click += lambda sender, event: dialog.Close()
    grid.KeyDown += keydown
    dialog.Closed += remember
    dialog.DefaultButton, dialog.AbortButton = ok, cancel
    layout = F.DynamicLayout()
    layout.Spacing = E.Size(8, 8)
    label = F.Label()
    label.Text = 'Select clipping sections (Ctrl / Shift for multiple)'
    layout.AddRow(label)
    layout.Add(grid, yscale=True)
    layout.AddSeparateRow(None, ok, cancel)
    dialog.Content = layout
    return dialog, grid


def select_clipping_list(labels):
    dialog, grid = clipping_dialog(labels)
    try:
        dialog.ShowModal(R.UI.RhinoEtoApp.MainWindow)
        return [labels[i] for i in (dialog.Tag or [])]
    finally:
        dialog.Dispose()


def resolve_clippings(planes, clipping_ids):
    """Resolve the complete request before modifying anything; preserve input order."""
    if isinstance(clipping_ids, STRING_TYPES):
        clipping_ids = re.split(r'[,;\s]+', clipping_ids.strip())
    if not clipping_ids: raise ValueError('At least one clipping plane GUID is required')
    available = {str(cp.Id).lower(): cp for cp in planes}
    selected, seen = [], set()
    for value in clipping_ids:
        try: key = str(uuid.UUID(str(value)))
        except (ValueError, TypeError, AttributeError):
            raise ValueError('Invalid clipping plane GUID: '+str(value))
        if key not in available:
            raise ValueError('Clipping plane not found in this document: '+key)
        if key not in seen:
            selected.append(available[key])
            seen.add(key)
    return selected


def select_clippings(planes, caller='User'):
    import rhinoscriptsyntax as rs
    labels = ['{0}: {1} [{2}] | {3}'.format(i+1, cp.Name or 'Unnamed', cp.Id,
              cp.Document.Layers[cp.Attributes.LayerIndex].FullPath)
              for i, cp in enumerate(planes)]
    if caller == 'User':
        selected = select_clipping_list(labels)
        return [cp for label, cp in zip(labels, planes) if label in (selected or [])]
    while True:
        answer = rs.GetString('Clipping plane GUIDs (comma or space separated)')
        if answer is None: return []
        try:
            return resolve_clippings(planes, answer)
        except ValueError as error:
            print(error)


def default_options(operation='Create'):
    modes = {'Create': 'Document', 'Update': 'Update', 'Move': 'Placement', 'PDF': 'PDF'}
    if operation not in modes: raise ValueError('Expected Create, Update, Move or PDF')
    return dict(mode=modes[operation], hatch=True, elevation=True, pick=False, small_details=True,
                near_width=.09, far_width=.04, near_dark=80., far_dark=45.)


def get_options(operation='Create'):
    import scriptcontext as sc
    keys = ('near_width', 'far_width', 'near_dark', 'far_dark')
    values = default_options(operation)
    values.update(zip(keys, sc.sticky.get('PlanSection:style_defaults', [.09, .04, 80., 45.])))
    values.update(sc.sticky.get('PlanSection:options', {}))
    values['mode'] = default_options(operation)['mode']
    if operation != 'Create': values['pick'] = False
    if operation == 'Move': return values
    print('SmallDetails='+('Keep' if values['small_details'] else 'Omit'))
    print('Output={mode}, Hatch={hatch}, Elevation={elevation}, PickPlacement={pick}; '
          'Near/Far width={near_width}/{far_width} mm, darkness={near_dark}/{far_dark}%'.format(**values))
    getter = R.Input.Custom.GetOption()
    getter.SetCommandPrompt('PlanSection: Enter to proceed, Change to edit options')
    getter.AcceptNothing(True)
    getter.AddOption('Change')
    try:
        result = getter.Get()
        if result == R.Input.GetResult.Option:
            toggle_keys = [('Hatch','hatch'), ('Elevation','elevation')]
            if operation == 'Create': toggle_keys.append(('PickPlacement','pick'))
            toggles = [(name, key, R.Input.Custom.OptionToggle(values[key], 'False', 'True'))
                       for name, key in toggle_keys]
            toggles.append(('SmallDetails', 'small_details',
                            R.Input.Custom.OptionToggle(values['small_details'], 'Omit', 'Keep')))
            numbers = [(name, key, R.Input.Custom.OptionDouble(values[key], .001, System.Double.MaxValue)
                        if key.endswith('width') else R.Input.Custom.OptionDouble(values[key], 0., 100.))
                       for name, key in zip(('NearWidth','FarWidth','NearDark','FarDark'), keys)]
            modes = ['Document', 'Files']
            getter.SetCommandPrompt('PlanSection options: Enter to run (width mm, darkness 0-100%)')
            while True:
                getter.ClearCommandOptions()
                mode_index = (getter.AddOptionList('Output', modes, modes.index(values['mode']))
                              if operation == 'Create' else None)
                for name, key, option in toggles: getter.AddOptionToggle(name, option)
                for name, key, option in numbers: getter.AddOptionDouble(name, option)
                result = getter.Get()
                if result == R.Input.GetResult.Option:
                    if getter.OptionIndex() == mode_index:
                        values['mode'] = modes[getter.Option().CurrentListOptionIndex]
                    continue
                if result != R.Input.GetResult.Nothing: return None
                values.update((key, option.CurrentValue) for name, key, option in toggles+numbers)
                try:
                    validate_options(*(values[key] for key in keys))
                    break
                except ValueError as error:
                    print(error)
        elif result != R.Input.GetResult.Nothing:
            return None
        sc.sticky['PlanSection:style_defaults'] = [values[key] for key in keys]
        sc.sticky['PlanSection:options'] = dict(values)
        return values
    finally:
        getter.Dispose()


def process_clipping(doc, cp, options, folder, progress, is_cancelled, model_cache=None,
                     target=None, result=None):
    """Handle one output and release only the newly generated, caller-owned geometry."""
    mode = options['mode']
    pick = options['pick'] and mode not in ('Update', 'PDF') and target is None
    near_width, far_width, near_dark, far_dark = [options[key]
        for key in ('near_width','far_width','near_dark','far_dark')]
    drawing = None
    try:
        if mode == 'Placement':
            if not reposition_drawing(doc, cp, target): return 'cancelled'
            print('Moved: '+(cp.Name or str(cp.Id)))
            return 'completed'
        cut = cp.ClippingPlaneGeometry.Plane
        if mode == 'PDF':
            paper, scale = pdf_settings(cp)
            print('{0}: Paper={1}*{2} mm; Scale=1:{3}'.format(cp.Name, paper[0], paper[1], scale))
        placement = G.Plane.WorldXY if mode == 'PDF' else (cut if pick else target)
        if mode == 'Update':
            existing = drawing_objects(doc, cp)
            if not existing:
                print('SKIPPED {0}: no existing local drawing; use Create first.'.format(cp.Name or cp.Id))
                return 'skipped'
            placement = saved_placement(cp, existing)
        drawing = generate(doc, cp, options['hatch'], options['elevation'], placement,
                           near_width, far_width, near_dark, far_dark, progress, place=not pick,
                           small_details=options['small_details'], model_cache=model_cache)
        if pick and drawing['objects']:
            R.RhinoApp.Wait()
            if is_cancelled(): return 'cancelled'
            target = pick_placement(drawing, cut, cp.Name or str(cp.Id))
            if target is None: return 'cancelled'
            move_drawing(drawing, cut, target)
        if mode == 'PDF':
            path = export_pdf(doc, drawing, folder, cp.Name or str(cp.Id), paper, scale)
            if result is not None: result['path'] = path
            print('Exported: '+path)
        elif mode == 'Files':
            path = export_drawing(doc, drawing, folder, cp.Name or str(cp.Id))
            if result is not None: result['path'] = path
            print('Exported: '+path)
            if target is not None and not cp.IsReference:
                attrs = cp.Attributes.Duplicate()
                attrs.SetUserString('draft_plane', plane_json(target))
                if not doc.Objects.ModifyAttributes(cp.Id, attrs, True):
                    raise ValueError('3dm exported, but draft_plane could not be saved')
        else:
            ids = bake(doc, cp, drawing, target)
            if result is not None: result['object_ids'] = [str(value) for value in ids]
        if result is not None: result['report'] = drawing['report']
        print('{0}: {1}'.format(cp.Name or cp.Id, drawing['report']))
        return 'completed'
    finally:
        if drawing is not None:
            dispose_drawing_items(drawing['objects'])


def run_selected(doc, planes, options, folder=None, targets=None):
    """Shared batch lifecycle. Results distinguish failure, skip and cancellation."""
    mode = options['mode']
    targets = targets or {}
    results = []
    if mode == 'Update':
        print('Update: regenerate existing drawings at saved placement; PickPlacement is not used.')
    if mode == 'PDF':
        print('PDF: clipping origin at paper center; outside paper is cropped; PickPlacement is not used.')
    serial = doc.BeginUndoRecord('PlanSection') if mode != 'PDF' else 0
    done = 0
    cancelled = [False]
    def cancel(sender, event): cancelled[0] = True
    R.RhinoApp.EscapeKeyPressed += cancel
    def progress(stage):
        print(stage)
        R.RhinoApp.Wait()
        if cancelled[0]: raise RuntimeError('Cancelled')
    model_cache = None
    try:
        if mode != 'Placement' and len(planes)>1: model_cache = ModelCache(doc)
        for cp in planes:
            R.RhinoApp.Wait()
            if cancelled[0]: break
            item = dict(clipping_id=str(cp.Id), name=cp.Name, status='failed')
            results.append(item)
            try:
                status = process_clipping(doc, cp, options, folder, progress, lambda: cancelled[0], model_cache,
                                          targets.get(str(cp.Id).lower()), item)
                item['status'] = status
                if status == 'cancelled': break
                if status == 'completed': done += 1
            except Exception as error:
                item['error'] = str(error)
                if cancelled[0]: item['status'] = 'cancelled'
                print('FAILED {0}: {1}'.format(cp.Name or cp.Id, error))
        print('Completed {0}/{1} drawings. {2}'.format(done, len(planes),
              'Exported files remain after Undo.' if mode in ('Files','PDF') else 'Undo reverses this run.'))
    finally:
        if model_cache is not None: model_cache.Dispose()
        R.RhinoApp.EscapeKeyPressed -= cancel
        if serial: doc.EndUndoRecord(serial)
        doc.Views.Redraw()
    return dict(status=('cancelled' if cancelled[0] or any(i['status']=='cancelled' for i in results)
                        else 'completed' if done == len(planes) else 'partial'),
                completed=done, requested=len(planes), results=results)


def run(doc, operation, clipping_ids, points=None, folder=None, output='Document',
        hatch=True, elevation=True, small_details=True,
        near_width=.09, far_width=.04, near_dark=80., far_dark=45.):
    """Agent entry: explicit document/GUIDs/XY points; never opens an input dialog.

    points maps clipping GUIDs to [x, y] or [x, y, 0] in document units.
    Move requires a point for every clipping. Create can use draft_plane defaults.
    """
    if doc is None: raise ValueError('A bound Rhino document is required')
    options = default_options(operation)
    if output not in ('Document', 'Files'): raise ValueError('Expected Document or Files output')
    if operation != 'Create' and output != 'Document':
        raise ValueError('Files output is only available for Create')
    if operation == 'Create': options['mode'] = output
    validate_options(near_width, far_width, near_dark, far_dark)
    options.update(hatch=hatch, elevation=elevation, small_details=small_details,
                   near_width=near_width, far_width=far_width, near_dark=near_dark, far_dark=far_dark)
    planes = resolve_clippings(clipping_planes(doc), clipping_ids)
    if points and operation not in ('Create', 'Move'):
        raise ValueError('Placement points apply only to Create or Move')
    targets = {}
    for key, value in (points or {}).items():
        cp = resolve_clippings(planes, [key])[0]
        if len(value) not in (2, 3) or not all(finite(float(n)) for n in value):
            raise ValueError('Placement requires finite [x, y] or [x, y, 0]')
        if len(value) == 3 and float(value[2]) != 0:
            raise ValueError('Drawing placement Z must be zero')
        targets[str(cp.Id).lower()] = placement_plane(G.Plane.WorldXY, G.Point3d(float(value[0]), float(value[1]), 0))
    if operation == 'Move' and len(targets) != len(planes):
        raise ValueError('Move requires a placement point for every clipping GUID')
    if options['mode'] in ('Files', 'PDF') and (not folder or not os.path.isdir(folder)):
        raise ValueError('An existing output folder is required for Files/PDF')
    return run_selected(doc, planes, options, folder, targets)


def main(doc=None):
    import rhinoscriptsyntax as rs
    doc = doc or R.RhinoDoc.ActiveDoc
    if doc is None: raise ValueError('Open a Rhino document first')
    caller = rs.GetString('Clipping selection: User opens list; Agent enters GUIDs', 'User', ['User', 'Agent'])
    if caller is None: return
    operation = rs.GetString('PlanSection operation', 'Create', ['Create', 'Update', 'Move', 'PDF'])
    if operation is None: return
    planes = clipping_planes(doc)
    if not planes:
        print('No clipping planes in this document')
        return
    planes = select_clippings(planes, caller)
    if not planes: return
    options = get_options(operation)
    if options is None: return
    folder = None
    if options['mode'] in ('Files', 'PDF'):
        folder = rs.BrowseForFolder(message='Folder for individual drawing files', title='PlanSection')
        if not folder: return
    return run_selected(doc, planes, options, folder)


if __name__ == '__main__':
    main()
