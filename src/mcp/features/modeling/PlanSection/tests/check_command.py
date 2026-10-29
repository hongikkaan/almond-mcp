# -*- coding: utf-8 -*-
"""Drive the real command on TEST with scripted UI answers; no live document."""
import hashlib, json, os, shutil, sys, tempfile, traceback
import Rhino as R
import System
import rhinoscriptsyntax as rs
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0,ROOT)
import PlanSection as ps


def sha(path):
    digest = hashlib.sha256()
    with open(path,'rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()


def fingerprint(objects):
    return dict((str(o.Id),(int(o.Geometry.DataCRC(0)),o.Attributes.ToJSON(None))) for o in objects)


out = os.environ.get('PLANSECTION_TEST_OUTPUT') or os.path.join(tempfile.gettempdir(),'PlanSection-checks')
if not os.path.isdir(out): os.makedirs(out)
work = tempfile.mkdtemp(prefix='PlanSection-command-')
originals = ps.select_clippings,ps.get_options,ps.pick_placement,rs.BrowseForFolder,rs.GetString
doc = None
report = dict(passed=False,rhino=str(R.RhinoApp.Version))
try:
    path = os.path.join(ROOT,'TEST.3dm')
    before = sha(path)
    report['code_sha256'] = sha(os.path.join(ROOT,'PlanSection.py'))
    doc = R.RhinoDoc.OpenHeadless(path)
    if doc is None: raise IOError('Cannot open TEST.3dm')
    cp = next(cp for cp in ps.clipping_planes(doc) if cp.Name=='3F')
    clip_id = cp.Id
    source_objects = [o for o in ps.objects(doc) if o.Id != clip_id]
    for definition in doc.InstanceDefinitions:
        if not definition.IsDeleted: source_objects.extend(definition.GetObjects())
    source = fingerprint(source_objects)
    options = dict(mode='Document',hatch=True,elevation=True,pick=True,small_details=False,
                   near_width=.09,far_width=.04,near_dark=80.,far_dark=45.)
    picked = [ps.placement_plane(R.Geometry.Plane.WorldXY,R.Geometry.Point3d(1234,-567,0))]
    ps.select_clippings = lambda planes,caller:[p for p in planes if p.Id==clip_id]
    ps.get_options = lambda operation:dict(options)
    rs.GetString = lambda prompt,default,choices: (dict(Document='Create',Files='Create',Placement='Move').get(options['mode'],options['mode'])
                                                  if choices[0]=='Create' else 'User')
    ps.pick_placement = lambda *args:picked[0]
    rs.BrowseForFolder = lambda **kwargs:work
    def existing(): return ps.drawing_objects(doc,doc.Objects.FindId(clip_id))
    ps.main(doc)
    first = set(o.Id for o in existing())
    assert first and all(o.Geometry.IsValid for o in existing()), 'Document output missing/disposed'
    assert ps.saved_placement(doc.Objects.FindId(clip_id),existing()) == picked[0]
    options['mode'] = 'Placement'
    picked[0] = ps.placement_plane(R.Geometry.Plane.WorldXY,R.Geometry.Point3d(2468,-1134,0))
    ps.main(doc)
    assert set(o.Id for o in existing()) == first and all(o.Geometry.IsValid for o in existing())
    assert ps.saved_placement(doc.Objects.FindId(clip_id),existing()) == picked[0]
    options['mode'] = 'Update'
    ps.main(doc)
    updated = set(o.Id for o in existing())
    assert updated and not updated.intersection(first) and all(o.Geometry.IsValid for o in existing())
    assert ps.saved_placement(doc.Objects.FindId(clip_id),existing()) == picked[0]
    options['mode'],picked[0] = 'Document',None
    snapshot = fingerprint(ps.objects(doc))
    ps.main(doc)
    assert fingerprint(ps.objects(doc)) == snapshot, 'Cancelled pick changed existing output'
    options['pick'] = False
    selected = set(cp.Id for cp in ps.clipping_planes(doc) if cp.Name in ('3F','Sec-D'))
    assert len(selected)==2, 'Missing multi-clipping command input'
    ps.select_clippings = lambda planes,caller:[p for p in planes if p.Id in selected]
    for mode in ('Files','PDF'):
        options['mode'] = mode
        ps.main(doc)
        assert fingerprint(ps.objects(doc)) == snapshot, mode+' changed document'
    exported = [name for name in os.listdir(work) if name.endswith('.3dm')]
    assert len(exported)==2 and len([n for n in os.listdir(work) if n.endswith('.pdf')])==2
    for name in exported:
        with R.FileIO.File3dm.Read(os.path.join(work,name)) as model:
            assert model.Objects.Count > 0 and all(o.Geometry.IsValid for o in model.Objects)
    assert fingerprint(source_objects)==source and sha(path)==before, 'Source changed'
    assert report['code_sha256']==sha(os.path.join(ROOT,'PlanSection.py'))
    report.update(passed=True,modes=['Document','Placement','Update','cancel','Files','PDF'],
                  file_sha256=before,source_unchanged=True,output_valid_after_release=True,
                  multi_clipping_exports=['3F','Sec-D'])
    System.Console.WriteLine('COMMAND_PASS: actual command modes, native output survives temporary geometry release')
except Exception:
    report['error'] = traceback.format_exc()
    raise
finally:
    ps.select_clippings,ps.get_options,ps.pick_placement,rs.BrowseForFolder,rs.GetString = originals
    if doc is not None: doc.Dispose()
    shutil.rmtree(work)
    with open(os.path.join(out,'command.json'),'w') as stream: json.dump(report,stream,indent=2)
