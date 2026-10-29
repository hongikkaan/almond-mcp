# -*- coding: utf-8 -*-
import os, sys, json, time, traceback, hashlib, tempfile, shutil
import Rhino as R
import System
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
import PlanSection as ps

def file_hash(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''): digest.update(chunk)
    return digest.hexdigest()

def fingerprint(doc):
    digest = hashlib.sha256()
    objects = ps.objects(doc)
    for definition in doc.InstanceDefinitions:
        if not definition.IsDeleted: objects.extend(definition.GetObjects())
    for obj in sorted(objects, key=lambda o: str(o.Id)):
        digest.update((str(obj.Id) + ':' + str(obj.Geometry.DataCRC(0)) + ':' + obj.Attributes.ToJSON(None)).encode('utf-8'))
    for layer in doc.Layers:
        if not layer.IsDeleted: digest.update(layer.ToJSON(None).encode('utf-8'))
    return digest.hexdigest()

path = os.path.join(ROOT, 'TEST.3dm')
OUT = os.environ.get('PLANSECTION_TEST_OUTPUT') or os.path.join(tempfile.gettempdir(), 'PlanSection-checks')
if not os.path.isdir(OUT): os.makedirs(OUT)
output = os.path.join(OUT, 'model.json')
report = dict(code_sha256=file_hash(os.path.join(ROOT,'PlanSection.py')), model='TEST.3dm', rhino=str(R.RhinoApp.Version), passed=False, drawings=[])
doc = None
try:
    file_before = report['file_before'] = file_hash(path)
    doc = R.RhinoDoc.OpenHeadless(path)
    if doc is None: raise IOError('Cannot open TEST.3dm')
    before = fingerprint(doc)
    modified = doc.Modified
    kinds = {}
    for obj in ps.objects(doc):
        name = obj.Geometry.GetType().Name
        kinds[name] = kinds.get(name, 0) + 1
    planes = ps.clipping_planes(doc)
    report.update(objects=kinds, units=str(doc.ModelUnitSystem), tolerance=doc.ModelAbsoluteTolerance,
                  clipping=[dict(name=cp.Name, id=str(cp.Id)) for cp in planes], source_before=before)
    expected = set(['Sec-A','Sec-B','Sec-C','Sec-D','RF','6F','5F','4F','3F','2F','1F','B1F'])
    assert set(cp.Name for cp in planes) == expected and len(planes) == len(expected), 'Unexpected section clipping selection'
    # This saved fixture starts at Z=7000 mm. These downward-facing cuts are below it.
    empty = set(['B1F','1F','2F'])
    for cp in planes:
        for keep in (True, False):
            entry = dict(name=cp.Name, mode='Keep' if keep else 'Omit')
            drawing = None
            started = time.time()
            System.Console.WriteLine('{0} {1}: generate'.format(cp.Name, entry['mode']))
            try:
                drawing = ps.generate(doc, cp, small_details=keep)
                entry.update(drawing['report'])
                entry['expected_empty'] = cp.Name in empty
                if entry['expected_empty']:
                    assert not drawing['objects'] and entry['sources'] == 0, 'Expected no model below this clipping plane'
                    assert entry['skipped'].get('outside_depth') == 2294, 'Unexpected source filtering'
                else:
                    assert set(item['role'] for item in drawing['objects']) == set(['section','hatch','elevation']), 'Missing drawing output'
                assert all(item['geometry'].IsValid for item in drawing['objects']), 'Invalid output'
                assert all(abs(item['geometry'].GetBoundingBox(True).Min.Z) <= doc.ModelAbsoluteTolerance
                           and abs(item['geometry'].GetBoundingBox(True).Max.Z) <= doc.ModelAbsoluteTolerance
                           for item in drawing['objects']), 'Output is not WorldXY'
                if cp.Name == '3F' and keep:
                    work = tempfile.mkdtemp(prefix='PlanSection-export-')
                    reopened = None
                    try:
                        exported = ps.export_drawing(doc,drawing,work,'3F')
                        reopened = R.RhinoDoc.OpenHeadless(exported)
                        assert reopened is not None, 'Cannot reopen exported drawing'
                        result = ps.objects(reopened)
                        assert len(result) == len(drawing['objects']) and all(o.Geometry.IsValid for o in result)
                        assert reopened.ModelUnitSystem == doc.ModelUnitSystem
                        assert reopened.ModelAbsoluteTolerance == doc.ModelAbsoluteTolerance
                        assert all(o.Attributes.GetUserString('ps:placement') for o in result)
                        report['export_reopen'] = True
                    finally:
                        if reopened is not None: reopened.Dispose()
                        shutil.rmtree(work)
                    paper,scale = ps.pdf_settings(cp)
                    pdf_drawing = ps.generate(doc,cp,target=R.Geometry.Plane.WorldXY)
                    try:
                        report['pdf'] = dict(file=ps.export_pdf(doc,pdf_drawing,OUT,'3F',paper,scale),paper_mm=paper,scale=scale)
                    finally:
                        for item in pdf_drawing['objects']: item['geometry'].Dispose()
                entry['passed'] = True
            except Exception:
                entry.update(passed=False, error=traceback.format_exc())
            finally:
                if drawing is not None:
                    for item in drawing['objects']: item['geometry'].Dispose()
            entry['seconds'] = round(time.time()-started, 2)
            report['drawings'].append(entry)
            with open(output, 'w') as stream: json.dump(report, stream, indent=2, separators=(',', ': '))
            System.Console.WriteLine(json.dumps(entry))
    report['source_after'] = fingerprint(doc)
    report['file_after'] = file_hash(path)
    report['source_unchanged'] = (before == report['source_after'] and doc.Modified == modified
                                  and file_before == report['file_after'])
    report['passed'] = report['source_unchanged'] and all(entry['passed'] for entry in report['drawings'])
    if not report['passed']: raise RuntimeError('TEST.3dm checks failed; see ' + output)
    System.Console.WriteLine('Report: '+output)
    System.Console.WriteLine('TEST_MODEL_PASS: {0} drawings; source unchanged'.format(len(report['drawings'])))
except Exception:
    report['passed'] = False
    report['error'] = traceback.format_exc()
    raise
finally:
    with open(output, 'w') as stream: json.dump(report, stream, indent=2, separators=(',', ': '))
    if doc is not None: doc.Dispose()
