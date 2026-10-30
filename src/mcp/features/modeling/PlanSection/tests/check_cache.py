# -*- coding: utf-8 -*-
"""Native cache-identity checks on a disposable copy of the existing TEST model."""
import hashlib, json, os, sys, tempfile
import Rhino as R

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0,ROOT)
import PlanSection as ps
G = R.Geometry


def sha(path):
    value = hashlib.sha256()
    with open(path,'rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            value.update(chunk)
    return value.hexdigest()


def stamp(obj):
    return dict(id=str(obj.Id),serial=int(obj.RuntimeSerialNumber),crc=int(obj.Geometry.DataCRC(0)))


def assert_changed(before,after,label):
    assert before['crc']!=after['crc'], label+' did not change geometry'
    assert (before['id'],before['serial'])!=(after['id'],after['serial']), label+' changed geometry without changing cache identity'


def run():
    path = os.path.join(ROOT,'TEST.3dm')
    original = sha(path)
    output = os.path.join(os.environ.get('PLANSECTION_TEST_OUTPUT') or
                          os.path.join(tempfile.gettempdir(),'PlanSection-checks'),'cache.json')
    if not os.path.isdir(os.path.dirname(output)): os.makedirs(os.path.dirname(output))
    report = dict(passed=False,rhino=str(R.RhinoApp.Version),code_sha256=sha(os.path.join(ROOT,'PlanSection.py')),
                  model_sha256=original,checks={})
    doc = R.RhinoDoc.OpenHeadless(path)
    try:
        planes = dict((cp.Name,cp) for cp in ps.clipping_planes(doc))
        cache = ps.ModelCache(doc)
        drawing = None
        try:
            snapshots = {}
            for name in ('3F','Sec-D'):
                clip = ps.read_clip(doc,planes[name])
                first = ps.model_objects(doc,clip,{},cache)
                second = ps.model_objects(doc,clip,{},cache)
                assert [r['source'] for r in first]==[r['source'] for r in second]
                assert all(a is not b and a['geometry'] is b['geometry'] and
                           a['attributes'] is not b['attributes'] and a['resolved'] is not b['resolved']
                           for a,b in zip(first,second)), 'Cache did not share only geometry'
                for entry in cache.entries.values():
                    if entry['geometry'] is not None:
                        snapshots[id(entry['geometry'])] = (entry['geometry'],entry['geometry'].DataCRC(0))
                drawing = ps.generate(doc,planes[name],model_cache=cache)
                assert all(geo.DataCRC(0)==crc for geo,crc in snapshots.values()), 'Prepared geometry was modified'
                if name=='3F':
                    for item in drawing['objects']: item['geometry'].Dispose()
                    drawing = None
            report['checks']['cache_reuse'] = dict(entries=len(cache.entries),prepared=len(snapshots))
            cache.Dispose()
            cache.Dispose()  # Idempotent command cleanup.
            assert all(item['geometry'].IsValid for item in drawing['objects']), 'Output borrowed cache geometry'
            try:
                ps.model_objects(doc,ps.read_clip(doc,planes['3F']),{},cache)
            except ValueError:
                pass
            else:
                raise AssertionError('Disposed cache was accepted')
        finally:
            cache.Dispose()
            if drawing is not None:
                for item in drawing['objects']: item['geometry'].Dispose()

        roots = [o for o in ps.objects(doc) if not o.IsReference]
        leaf = next(o for o in roots if isinstance(o.Geometry,(G.Brep,G.Mesh,G.Extrusion)) and o.Geometry.IsValid)
        before,oid = stamp(leaf),leaf.Id
        replacement = leaf.Geometry.Duplicate()
        try:
            assert replacement.Transform(G.Transform.Translation(13.,0.,0.))
            assert doc.Objects.Replace(oid,replacement), 'Replace failed'
        finally: replacement.Dispose()
        after = stamp(doc.Objects.FindId(oid))
        assert_changed(before,after,'Objects.Replace')
        report['checks']['replace'] = [before,after]

        leaf = doc.Objects.FindId(oid)
        before = stamp(leaf)
        new_id = doc.Objects.Transform(oid,G.Transform.Translation(0.,17.,0.),True)
        leaf = doc.Objects.FindId(new_id)
        assert leaf is not None, 'Objects.Transform failed'
        after = stamp(leaf)
        assert_changed(before,after,'Objects.Transform')
        report['checks']['transform'] = [before,after]

        before = stamp(leaf)
        edited = leaf.Geometry
        transformed = edited.Transform(G.Transform.Translation(0.,0.,19.))
        committed = leaf.CommitChanges() if transformed else False
        after = stamp(doc.Objects.FindId(leaf.Id))
        if before['crc']!=after['crc']:
            assert_changed(before,after,'Geometry/CommitChanges')
        report['checks']['commit_changes'] = dict(before=before,after=after,transformed=transformed,committed=committed)

        instance = next(o for o in roots if isinstance(o,R.DocObjects.InstanceObject)
                        and any(isinstance(c.Geometry,(G.Brep,G.Mesh,G.Extrusion)) for c in o.InstanceDefinition.GetObjects()))
        definition = instance.InstanceDefinition
        children = list(definition.GetObjects())
        index = next(i for i,c in enumerate(children) if isinstance(c.Geometry,(G.Brep,G.Mesh,G.Extrusion)))
        before = stamp(children[index])
        geometry = [c.Geometry.Duplicate() for c in children]
        try:
            assert geometry[index].Transform(G.Transform.Translation(23.,0.,0.))
            assert doc.InstanceDefinitions.ModifyGeometry(definition.Index,geometry,[c.Attributes.Duplicate() for c in children])
        finally:
            for geo in geometry: geo.Dispose()
        after = stamp(list(definition.GetObjects())[index])
        assert_changed(before,after,'InstanceDefinitions.ModifyGeometry')
        report['checks']['block_geometry'] = [before,after]
        report['file_unchanged'] = sha(path)==original
        assert report['file_unchanged'], 'Source file changed'
        report['passed'] = True
        SystemConsole = __import__('System').Console
        SystemConsole.WriteLine('CACHE_PASS '+json.dumps(report))
    finally:
        doc.Dispose()
        with open(output,'w') as stream: json.dump(report,stream,indent=2)


if __name__=='__main__': run()
