# -*- coding: utf-8 -*-
"""Partition the unchanged TEST input in memory; no generated model files or .rws UI."""
import hashlib, json, os, sys, time, traceback, tempfile, shutil
import Rhino as R
import System
HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import PlanSection as ps
G, D = R.Geometry, R.DocObjects
MODEL = os.path.join(ROOT, 'TEST.3dm')
OUT = os.environ.get('PLANSECTION_TEST_OUTPUT') or os.path.join(tempfile.gettempdir(), 'PlanSection-checks')
if not os.path.isdir(OUT): os.makedirs(OUT)
report = dict(passed=False, rhino=str(R.RhinoApp.Version), cases=[],
              reference_setup='Native reference layers/objects in memory; no .rws attach/reload')


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''): digest.update(chunk)
    return digest.hexdigest()


def fingerprint(objects):
    return dict((str(o.Id), (int(o.Geometry.DataCRC(0)), o.Attributes.ToJSON(None))) for o in objects)


def layer_fingerprint(doc):
    # Only the local Drawing root's ownership registry is intentionally mutable.
    return dict((str(layer.Id),layer.ToJSON(None)) for layer in doc.Layers
                if not layer.IsDeleted and layer.FullPath != 'Drawing')


def source_objects(doc):
    objects = ps.objects(doc)
    for definition in doc.InstanceDefinitions:
        if not definition.IsDeleted: objects.extend(definition.GetObjects())
    return objects


def records(doc, cp):
    inputs = ps.model_objects(doc, ps.read_clip(doc, cp), {})
    try:
        return set((r['source'], int(r['geometry'].DataCRC(0)), r['attributes'].LayerIndex) for r in inputs)
    finally:
        for r in inputs: r['geometry'].Dispose()


def roots(sources):
    return set(System.Guid(s.split('/')[0]) for s in sources)


def clipping_signature(cp):
    geo = cp.ClippingPlaneGeometry
    ids,layers,exclude = geo.GetClipParticipation()
    return (cp.Name,ps.plane_json(geo.Plane),geo.PlaneDepthEnabled,geo.PlaneDepth,
            geo.ParticipationListsEnabled,sorted(str(i) for i in ids),sorted(layers),exclude,
            cp.Attributes.GetUserString('draft_plane'))


def attach(doc, source, selected_ids, name, serial):
    assert (source.ModelUnitSystem,source.ModelAbsoluteTolerance,source.ModelAngleToleranceRadians,source.ModelRelativeTolerance) == (doc.ModelUnitSystem,doc.ModelAbsoluteTolerance,doc.ModelAngleToleranceRadians,doc.ModelRelativeTolerance), 'Split reference units/tolerances differ'
    root = D.Layer()
    root.Name = name
    index = doc.Layers.CreateLayer(root, D.Tables.LayerTable.LayerType.WorkSessionParentLayer, serial, 0)
    assert index >= 0, 'Cannot create reference root'
    root_id = doc.Layers[index].Id
    layer_map = {}
    pending = [layer for layer in source.Layers if not layer.IsDeleted]
    while pending:
        advanced = False
        for layer in list(pending):
            if layer.ParentLayerId != System.Guid.Empty and layer.ParentLayerId not in layer_map: continue
            copy = D.Layer()
            copy.CopyAttributesFrom(layer)
            copy.Name = layer.Name
            copy.Id = System.Guid.NewGuid()
            copy.ParentLayerId = root_id if layer.ParentLayerId == System.Guid.Empty else doc.Layers[layer_map[layer.ParentLayerId]].Id
            index = doc.Layers.CreateLayer(copy, D.Tables.LayerTable.LayerType.NormalLayer, serial, 0)
            assert index >= 0, 'Cannot create reference child layer'
            layer_map[layer.Id] = index
            pending.remove(layer)
            advanced = True
        assert advanced, 'Unresolved reference layer hierarchy'
    added = []
    selected = [o for o in ps.objects(source) if o.Id in selected_ids]
    instances = set(o.Id for o in selected if isinstance(o,D.InstanceObject))
    for obj in selected:
        if isinstance(obj,D.InstanceObject): continue
        attrs = obj.Attributes.Duplicate()
        attrs.ObjectId = obj.Id
        attrs.LayerIndex = layer_map[source.Layers[obj.Attributes.LayerIndex].Id]
        if isinstance(obj, D.ClippingPlaneObject):
            oid = doc.Objects.AddClippingPlaneSurface(obj.ClippingPlaneGeometry, attrs, None, True)
        else:
            oid = doc.Objects.Add(obj.Geometry, attrs, None, True)
        assert oid != System.Guid.Empty, 'Cannot add reference '+obj.GetType().Name+': '+str(obj.Id)
        assert oid == obj.Id, 'Reference GUID changed'
        result = doc.Objects.FindId(oid)
        assert result is not None and result.IsReference, 'Object is not a native reference'
        added.append(result)
    # Headless Rhino cannot add reference instances against local definitions.
    # Reference block leaves are copied in memory; active blocks remain intact.
    clip = dict(plane=G.Plane.WorldXY,depth=None,enabled=True,ids=instances,layers=set(),exclude=False)
    inputs = ps.model_objects(source,clip,{}) if instances else []
    try:
        for item in inputs:
            attrs = item['attributes'].Duplicate()
            attrs.ObjectId = System.Guid.NewGuid()
            attrs.LayerIndex = layer_map[source.Layers[attrs.LayerIndex].Id]
            oid = doc.Objects.Add(item['geometry'],attrs,None,True)
            result = doc.Objects.FindId(oid)
            assert result is not None and result.IsReference, 'Cannot add reference block leaf'
            added.append(result)
    finally:
        for item in inputs: item['geometry'].Dispose()
    return added


def drawing_check(drawing, active_ids, tol):
    counts = dict(section=0, hatch=0, elevation=0)
    box = G.BoundingBox.Empty
    for item in drawing['objects']:
        geometry = item['geometry']
        assert geometry.IsValid, 'Invalid output'
        bounds = geometry.GetBoundingBox(True)
        assert bounds.IsValid and abs(bounds.Min.Z) <= tol and abs(bounds.Max.Z) <= tol, 'Output is not Z=0'
        box.Union(bounds)
        counts[item['role']] += 1
        sources = json.loads(item['attributes'].GetUserString('ps:sources') or '[]')
        assert sources and roots(sources) <= active_ids, 'Attached source entered output'
    assert all(counts.values()), 'Missing output role: '+str(counts)
    return box, counts


def dispose(drawing):
    for item in drawing['objects']: item['geometry'].Dispose()


def check_ownership(doc, cp, drawing, ids, moved):
    doc.UndoRecordingEnabled = True
    serial = doc.BeginUndoRecord('replacement ownership check')
    try:
        replacement = set(ps.bake(doc,cp,drawing))
    finally:
        doc.EndUndoRecord(serial)
    assert replacement and not replacement.intersection(ids)
    assert set(o.Id for o in ps.drawing_objects(doc,cp)) == replacement
    assert doc.Undo(), 'Replacement Undo unavailable'
    assert set(o.Id for o in ps.drawing_objects(doc,cp)) == ids, 'Registry did not follow Undo'
    assert ps.saved_placement(cp,ps.drawing_objects(doc,cp)) == moved
    baseline = fingerprint(ps.objects(doc))
    original_save = ps.save_drawing_registry
    def fail_registry(*args): raise ValueError('injected registry failure')
    ps.save_drawing_registry = fail_registry
    try:
        try:
            ps.bake(doc,cp,drawing)
        except ValueError as error:
            assert str(error) == 'injected registry failure'
        else:
            raise AssertionError('Failed registry write was ignored')
    finally:
        ps.save_drawing_registry = original_save
    assert fingerprint(ps.objects(doc)) == baseline, 'Failed bake changed existing objects'
    assert set(o.Id for o in ps.drawing_objects(doc,cp)) == ids
    folder = tempfile.mkdtemp(prefix='PlanSection-ownership-')
    reopened = None
    try:
        path = os.path.join(folder,'output.3dm')
        assert doc.Write3dmFile(path,R.FileIO.FileWriteOptions())
        reopened = R.RhinoDoc.OpenHeadless(path)
        assert reopened is not None
        assert set(o.Id for o in ps.drawing_objects(reopened,cp)) == ids, 'Ownership lost after reopen'
        assert ps.saved_placement(cp,ps.drawing_objects(reopened,cp)) == moved
    finally:
        if reopened is not None: reopened.Dispose()
        shutil.rmtree(folder)
    report.setdefault('ownership',[]).append(dict(clip=str(cp.Id),undo=True,
        failed_bake_retained=True,reopened=True,manual_edit_retained=True))


def run_model(name, expected, other, source, original, shared_planes, settings):
    doc = R.RhinoDoc.OpenHeadless(MODEL)
    if doc is None: raise IOError('Cannot open '+name)
    try:
        assert (doc.ModelUnitSystem,doc.ModelAbsoluteTolerance,doc.ModelAngleToleranceRadians,doc.ModelRelativeTolerance) == settings
        for obj in ps.objects(doc):
            if obj.Id not in expected:
                assert doc.Objects.Purge(obj.RuntimeSerialNumber), 'Cannot purge excluded root '+str(obj.Id)
        active = ps.objects(doc)
        active_ids = set(o.Id for o in active)
        assert active_ids == expected, 'Partition changed model IDs'
        snapshot = fingerprint(source_objects(doc))
        assert all(original.get(key) == value for key,value in snapshot.items()), 'Partition changed source records'
        references = attach(doc, source, other, 'model_B' if name=='model_A' else 'model_A', 1001)
        assert not active_ids.intersection(o.Id for o in references)
        clips = attach(doc, source, set(shared_planes), 'clipping', 1002)
        assert len(clips) == 12 and all(isinstance(o,D.ClippingPlaneObject) for o in clips)
        assert set(o.Id for o in clips) == set(shared_planes), 'Shared clipping IDs changed'
        for cp in clips:
            assert clipping_signature(cp) == shared_planes[cp.Id], 'Shared clipping plane/depth/placement changed'
        planes = dict((cp.Name,cp) for cp in ps.clipping_planes(doc))
        cp = planes['3F']
        attrs = cp.Attributes.Duplicate()
        attrs.ObjectId = System.Guid.NewGuid()
        attrs.LayerIndex = doc.Layers.AddPath(ps.CLIP_LAYER)
        geometry = cp.ClippingPlaneGeometry.Duplicate()
        try:
            geometry.ParticipationListsEnabled = False
            oid = doc.Objects.AddClippingPlaneSurface(geometry, attrs, None, False)
        finally:
            geometry.Dispose()
        local_cp = doc.Objects.FindId(oid)
        assert local_cp is not None and not local_cp.IsReference
        before_records = records(doc,cp)
        assert before_records and before_records == records(doc,local_cp), 'Local/reference input scope differs'
        used_roots = roots(s for s,crc,layer in before_records)
        assert used_roots <= active_ids, 'Attached model entered input records'
        contributors = sorted([o for o in active if o.Id in used_roots],key=lambda o: (not isinstance(o,D.InstanceObject),str(o.Id)))
        assert len(contributors) >= 2, 'Need two contributing active objects'
        hidden,locked = contributors[:2]
        for obj in [hidden,locked]:
            doc.Objects.Unlock(obj.Id,True)
            doc.Objects.Show(obj.Id,True)
        assert doc.Objects.Hide(hidden.Id,True)
        assert doc.Objects.Lock(locked.Id,True)
        assert doc.Objects.FindId(hidden.Id).IsHidden and doc.Objects.FindId(locked.Id).IsLocked
        layer_index = next(iter(before_records))[2]
        layer = doc.Layers[layer_index]
        layer.IsVisible, layer.IsLocked = False, True
        assert doc.Layers.Modify(layer,layer_index,True), 'Cannot hide/lock active source layer'
        assert not doc.Layers[layer_index].IsVisible and doc.Layers[layer_index].IsLocked
        assert before_records == records(doc,cp) == records(doc,local_cp), 'Hidden/locked input was excluded'
        baseline = fingerprint(source_objects(doc))
        source_layers = layer_fingerprint(doc)
        original_ids = set(baseline)
        tol = doc.ModelAbsoluteTolerance
        for clip_name in ['3F','Sec-D']:
            cp = planes[clip_name]
            for keep in [True,False]:
                started = time.time()
                modified = doc.Modified
                drawing = ps.generate(doc,cp,small_details=keep)
                try:
                    assert doc.Modified == modified, 'Generation changed document save state'
                    box,counts = drawing_check(drawing,active_ids,tol)
                    report['cases'].append(dict(model=name,clip=clip_name,mode='Keep' if keep else 'Omit',counts=counts,seconds=round(time.time()-started,2)))
                    System.Console.WriteLine('{0} {1} {2}: PASS {3}'.format(name,clip_name,'Keep' if keep else 'Omit',counts))
                    if clip_name != '3F' or not keep: continue
                    shared = ps.draft_plane(cp.Attributes.GetUserString('draft_plane'))
                    assert ps.read_clip(doc,cp)['target'] == shared
                    ids = set(ps.bake(doc,cp,drawing))
                    assert ids and all(not doc.Objects.FindId(i).IsReference for i in ids), 'Bake was not local'
                    edited_id = sorted([i for i in ids if isinstance(doc.Objects.FindId(i).Geometry,G.Curve)],key=str)[0]
                    edited_attrs = doc.Objects.FindId(edited_id).Attributes.Duplicate()
                    edited_attrs.Name = 'Manual edit to preserve'
                    edited_attrs.ObjectColor = ps.Color.Magenta
                    edited_attrs.ColorSource = D.ObjectColorSource.ColorFromObject
                    edited_attrs.PlotWeightSource = D.ObjectPlotWeightSource.PlotWeightFromObject
                    edited_attrs.PlotWeight = .27
                    edited_geo = doc.Objects.FindId(edited_id).Geometry.Duplicate()
                    try:
                        assert edited_geo.Transform(G.Transform.Translation(7,-9,0))
                        assert doc.Objects.Replace(edited_id,edited_geo,True)
                    finally:
                        edited_geo.Dispose()
                    assert doc.Objects.ModifyAttributes(edited_id,edited_attrs,True)
                    delta = G.Vector3d(1234,-567,0)
                    moved = ps.placement_plane(shared,shared.Origin+delta)
                    expected_geo = doc.Objects.FindId(edited_id).Geometry.Duplicate()
                    try:
                        assert expected_geo.Transform(G.Transform.Translation(delta))
                        assert ps.reposition_drawing(doc,cp,moved)
                        assert expected_geo.DataCRC(0) == doc.Objects.FindId(edited_id).Geometry.DataCRC(0), 'Placement lost manual geometry'
                    finally:
                        expected_geo.Dispose()
                    existing = ps.drawing_objects(doc,cp)
                    assert set(o.Id for o in existing) == ids, 'Placement changed GUIDs'
                    actual_attrs = doc.Objects.FindId(edited_id).Attributes
                    assert actual_attrs.Name == edited_attrs.Name, 'Placement lost edited name'
                    assert actual_attrs.ObjectColor == edited_attrs.ObjectColor and actual_attrs.ColorSource == edited_attrs.ColorSource, 'Placement lost edited color'
                    assert actual_attrs.PlotWeight == edited_attrs.PlotWeight and actual_attrs.PlotWeightSource == edited_attrs.PlotWeightSource, 'Placement lost edited print weight'
                    saved = ps.saved_placement(cp,existing)
                    assert saved == moved and ps.read_clip(doc,cp)['target'] == shared
                    updated = ps.generate(doc,cp,target=saved)
                    try:
                        updated_box,updated_counts = drawing_check(updated,active_ids,tol)
                        # Repeated native HLD runs can segment the same input differently.
                        # Update must retain section/hatch results and the saved placement.
                        assert all(counts[role] == updated_counts[role] for role in ['section','hatch'])
                        assert updated_box.Min.DistanceTo(box.Min+delta) <= tol and updated_box.Max.DistanceTo(box.Max+delta) <= tol, 'Update lost placement'
                        assert all(ps.draft_plane(i['attributes'].GetUserString('ps:placement')) == moved for i in updated['objects'])
                        report.setdefault('placement_updates',[]).append(dict(model=name,before=counts,after=updated_counts,
                            min_distance=updated_box.Min.DistanceTo(box.Min+delta),max_distance=updated_box.Max.DistanceTo(box.Max+delta)))
                    finally:
                        dispose(updated)
                    check_ownership(doc,cp,drawing,ids,moved)
                finally:
                    dispose(drawing)
        after = fingerprint(o for o in source_objects(doc) if str(o.Id) in original_ids)
        assert after == baseline, 'Source objects/reference clipping/block members changed'
        final_layers = layer_fingerprint(doc)
        assert all(final_layers.get(key)==value for key,value in source_layers.items()), 'Source layers changed'
        assert not doc.Layers[layer_index].IsVisible and doc.Layers[layer_index].IsLocked
        report.setdefault('models',[]).append(dict(name=name,active_objects=len(active_ids),reference_objects=len(references),
            hidden_type=hidden.GetType().Name,locked_type=locked.GetType().Name,
            hidden_locked_preserved=True,placement_update=True,source_unchanged=True))
    finally:
        doc.Dispose()


source = None
try:
    report['code_sha256'] = sha(os.path.join(ROOT,'PlanSection.py'))
    report['file_before'] = sha(MODEL)
    source = R.RhinoDoc.OpenHeadless(MODEL)
    if source is None: raise IOError('Cannot open TEST.3dm')
    original = fingerprint(source_objects(source))
    ids = sorted([o.Id for o in ps.objects(source) if not isinstance(o,D.ClippingPlaneObject)],key=str)
    parts = [set(ids[part::2]) for part in range(2)]
    assert not parts[0].intersection(parts[1]) and parts[0].union(parts[1]) == set(ids)
    planes = dict((cp.Id,clipping_signature(cp)) for cp in ps.clipping_planes(source))
    settings = (source.ModelUnitSystem,source.ModelAbsoluteTolerance,source.ModelAngleToleranceRadians,source.ModelRelativeTolerance)
    run_model('model_A',parts[0],parts[1],source,original,planes,settings)
    run_model('model_B',parts[1],parts[0],source,original,planes,settings)
    assert any(m['hidden_type']=='InstanceObject' for m in report['models']), 'Hidden block was not exercised'
    assert any(m['locked_type']=='InstanceObject' for m in report['models']), 'Locked block was not exercised'
    assert fingerprint(source_objects(source)) == original, 'Master input changed'
    report['file_after'] = sha(MODEL)
    assert report['file_after'] == report['file_before'], 'Input 3dm bytes changed'
    assert report['code_sha256'] == sha(os.path.join(ROOT,'PlanSection.py')), 'Production code changed during check'
    report['passed'] = True
    System.Console.WriteLine('PASS: in-memory A/B, active sources, hidden/locked, shared origin, local bake, Placement/Update, source preservation')
except Exception:
    report['error'] = traceback.format_exc()
    raise
finally:
    if source is not None: source.Dispose()
    with open(os.path.join(OUT,'worksession.json'),'w') as stream:
        json.dump(report,stream,indent=2,separators=(',',': '))
