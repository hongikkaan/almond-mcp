# -*- coding: utf-8 -*-
"""Optional reported-model reproduction. Requires external originals; never captures 3dm fixtures."""
import hashlib, json, os, sys, tempfile, time, traceback
import Rhino as R
import System
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
import PlanSection as ps


def sha(path):
    digest = hashlib.sha256()
    with open(path,'rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()


def fingerprint(doc):
    objects = ps.objects(doc)
    for definition in doc.InstanceDefinitions:
        if not definition.IsDeleted: objects.extend(definition.GetObjects())
    rows = dict((str(o.Id),(int(o.Geometry.DataCRC(0)),o.Attributes.ToJSON(None))) for o in objects)
    rows.update(('layer:'+str(layer.Id),layer.ToJSON(None)) for layer in doc.Layers if not layer.IsDeleted)
    return rows


OUT = os.environ.get('PLANSECTION_TEST_OUTPUT') or os.path.join(tempfile.gettempdir(),'PlanSection-checks')
if not os.path.isdir(OUT): os.makedirs(OUT)
report = dict(passed=False,rhino=str(R.RhinoApp.Version),cases=[])
doc = None
try:
    paths = [os.environ[key] for key in ('PLANSECTION_MODEL','PLANSECTION_CLIPPING')]
    report['files_before'] = [sha(path) for path in paths]
    report['code_sha256'] = sha(os.path.join(ROOT,'PlanSection.py'))
    doc = R.RhinoDoc.OpenHeadless(paths[0])
    if doc is None: raise IOError('Cannot open housing model')
    with R.FileIO.File3dm.Read(paths[1]) as clipping_model:
        parent = System.Guid.Empty
        for part in ['shared-clipping']+ps.CLIP_LAYER.split('::'):
            layer = R.DocObjects.Layer()
            layer.Name,layer.ParentLayerId = part,parent
            kind = R.DocObjects.Tables.LayerTable.LayerType.WorkSessionParentLayer if parent == System.Guid.Empty else R.DocObjects.Tables.LayerTable.LayerType.NormalLayer
            index = doc.Layers.CreateLayer(layer,kind,1001,0)
            assert index >= 0, 'Cannot create reference clipping layer'
            parent = doc.Layers[index].Id
        planes = {}
        for obj in clipping_model.Objects:
            if isinstance(obj.Geometry,R.Geometry.ClippingPlaneSurface):
                attrs = obj.Attributes.Duplicate()
                attrs.LayerIndex = index
                oid = doc.Objects.AddClippingPlaneSurface(obj.Geometry,attrs,None,True)
                assert oid != System.Guid.Empty and doc.Objects.FindId(oid).IsReference
                cp = doc.Objects.FindId(oid)
                assert cp.Name not in planes, 'Duplicate shared clipping name: '+str(cp.Name)
                planes[cp.Name] = cp
    before,modified = fingerprint(doc),doc.Modified
    for name in os.environ.get('PLANSECTION_CASES','3F,4F,Sec-D,Sec-C,Sec-B,Sec-A').split(','):
        entry,drawing = dict(name=name),None
        started = time.time()
        def progress(stage): entry['stage'] = stage
        System.Console.WriteLine(name+': generate Omit')
        try:
            drawing = ps.generate(doc,planes[name],small_details=False,progress=progress)
            entry['report'] = drawing['report']
            assert all(i['geometry'].IsValid for i in drawing['objects']), 'Invalid output'
            assert all(abs(i['geometry'].GetBoundingBox(True).Min.Z) <= doc.ModelAbsoluteTolerance
                       and abs(i['geometry'].GetBoundingBox(True).Max.Z) <= doc.ModelAbsoluteTolerance
                       for i in drawing['objects']), 'Output is not Z=0'
            assert all(drawing['report'][role] > 0 for role in ['section','elevation']), 'Missing output role'
            # The reported 4F cuts none of the fill-enabled layers in this external model.
            assert (drawing['report']['hatch'] == 0 if name=='4F' else drawing['report']['hatch'] > 0), 'Unexpected hatch count'
            entry['passed'] = True
        except Exception:
            entry.update(passed=False,error=traceback.format_exc())
        finally:
            if drawing is not None:
                for item in drawing['objects']: item['geometry'].Dispose()
            entry['seconds'] = round(time.time()-started,2)
            report['cases'].append(entry)
            with open(os.path.join(OUT,'housing.json'),'w') as stream: json.dump(report,stream,indent=2)
            System.Console.WriteLine(json.dumps(entry))
            System.GC.Collect()
    report['files_after'] = [sha(path) for path in paths]
    report['source_unchanged'] = (fingerprint(doc) == before and doc.Modified == modified
                                and report['files_before'] == report['files_after'])
    assert report['source_unchanged'], 'Source changed'
    assert report['code_sha256'] == sha(os.path.join(ROOT,'PlanSection.py')), 'Code changed during check'
    report['passed'] = all(row['passed'] for row in report['cases'])
    assert report['passed'], 'Housing check failed; see housing.json'
except Exception:
    report.update(passed=False,error=traceback.format_exc())
    raise
finally:
    if doc is not None: doc.Dispose()
    with open(os.path.join(OUT,'housing.json'),'w') as stream: json.dump(report,stream,indent=2)
