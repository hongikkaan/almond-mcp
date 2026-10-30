# -*- coding: utf-8 -*-
"""Compare saved PlanSection revisions on the same real model without editing it."""
import hashlib, imp, inspect, json, math, os, sys, tempfile, time, traceback
import Rhino as R
import System

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
import PlanSection as current


def sha(path):
    value = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()


def fingerprint(doc):
    value = hashlib.sha256()
    objects = current.objects(doc)
    for definition in doc.InstanceDefinitions:
        if not definition.IsDeleted:
            objects.extend(definition.GetObjects())
    for obj in sorted(objects, key=lambda o: str(o.Id)):
        value.update((str(obj.Id)+':'+str(obj.Geometry.DataCRC(0))+':'+obj.Attributes.ToJSON(None)).encode('utf-8'))
    for layer in doc.Layers:
        if not layer.IsDeleted:
            value.update(layer.ToJSON(None).encode('utf-8'))
    return value.hexdigest()


def clock():
    return System.Diagnostics.Stopwatch.GetTimestamp()/float(System.Diagnostics.Stopwatch.Frequency)


def attach_clippings(doc, path):
    parent = System.Guid.Empty
    for part in ['benchmark-clipping']+current.CLIP_LAYER.split('::'):
        layer = R.DocObjects.Layer()
        layer.Name, layer.ParentLayerId = part, parent
        kind = R.DocObjects.Tables.LayerTable.LayerType.WorkSessionParentLayer if parent == System.Guid.Empty else R.DocObjects.Tables.LayerTable.LayerType.NormalLayer
        index = doc.Layers.CreateLayer(layer, kind, 1001, 0)
        if index < 0:
            raise ValueError('Cannot create reference clipping layer')
        parent = doc.Layers[index].Id
    with R.FileIO.File3dm.Read(path) as source:
        for obj in source.Objects:
            if isinstance(obj.Geometry, R.Geometry.ClippingPlaneSurface):
                attrs = obj.Attributes.Duplicate()
                attrs.LayerIndex = index
                oid = doc.Objects.AddClippingPlaneSurface(obj.Geometry, attrs, None, True)
                if oid == System.Guid.Empty or not doc.Objects.FindId(oid).IsReference:
                    raise ValueError('Cannot attach reference clipping')


class Timings(object):
    def __init__(self, module):
        self.module, self.original, self.rows, self.stack = module, {}, {}, []
        self.options = set(inspect.getargspec(module.generate).args)
        for name in ('model_objects', 'intersect', 'clean_closed_curve', 'planar_union',
                     'region_boundaries', 'create_hatches', 'sections', 'elevations',
                     'deduplicate', 'split_crossings', 'cleanup_elevations', 'move_drawing'):
            original = getattr(module, name)
            self.original[name] = original
            setattr(module, name, self.wrap(name, original))

    def wrap(self, name, function):
        def measured(*args, **kwargs):
            frame = [clock(), 0.0]
            self.stack.append(frame)
            try:
                result = function(*args, **kwargs)
                if name == 'clean_closed_curve' and result[0] and len(result[0]) == 1 and result[0][0] is args[0]:
                    self.rows.setdefault('closed_loop_passthrough', dict(calls=0))['calls'] += 1
                return result
            finally:
                elapsed = clock()-frame[0]
                self.stack.pop()
                if self.stack:
                    self.stack[-1][1] += elapsed
                row = self.rows.setdefault(name, dict(calls=0, inclusive_seconds=0., exclusive_seconds=0.))
                row['calls'] += 1
                row['inclusive_seconds'] += elapsed
                row['exclusive_seconds'] += elapsed-frame[1]
        return measured

    def reset(self):
        self.rows = {}

    def close(self):
        for name, original in self.original.items():
            setattr(self.module, name, original)


def metrics(drawing, doc):
    """Run after the timing interval. These are diagnostics, not geometric equivalence proof."""
    roles = {}
    for item in drawing['objects']:
        geo, attrs, role = item['geometry'], item['attributes'], item['role']
        if not geo.IsValid:
            raise ValueError('Invalid '+role)
        bounds = geo.GetBoundingBox(True)
        if abs(bounds.Min.Z) > doc.ModelAbsoluteTolerance or abs(bounds.Max.Z) > doc.ModelAbsoluteTolerance:
            raise ValueError('Output is not WorldXY')
        key = role+'|'+(attrs.GetUserString('ps:source_layer') or '')
        row = roles.setdefault(key, dict(count=0, length=0., area=0., bbox=None))
        row['count'] += 1
        box = [bounds.Min.X,bounds.Min.Y,bounds.Max.X,bounds.Max.Y]
        if row['bbox'] is None:
            row['bbox'] = box
        else:
            row['bbox'] = [min(row['bbox'][0],box[0]),min(row['bbox'][1],box[1]),
                           max(row['bbox'][2],box[2]),max(row['bbox'][3],box[3])]
        if isinstance(geo, R.Geometry.Curve):
            row['length'] += geo.GetLength()
        elif isinstance(geo, R.Geometry.Hatch):
            area = R.Geometry.AreaMassProperties.Compute(geo)
            try:
                if area is None:
                    raise ValueError('Cannot measure hatch area')
                row['area'] += area.Area
            finally:
                if area is not None:
                    area.Dispose()
    return roles


def run():
    out = os.environ.get('PLANSECTION_TEST_OUTPUT') or os.path.join(tempfile.gettempdir(),'PlanSection-checks')
    if not os.path.isdir(out):
        os.makedirs(out)
    path = os.environ.get('PLANSECTION_MODEL') or os.path.join(ROOT,'TEST.3dm')
    clipping = os.environ.get('PLANSECTION_CLIPPING')
    baseline = os.environ.get('PLANSECTION_BENCH_BASELINE')
    cases = [x.strip() for x in os.environ.get('PLANSECTION_BENCH_CASES','3F,Sec-D').split(',')]
    tolerances = [float(x) for x in os.environ.get('PLANSECTION_BENCH_TOLERANCES','0.5,1').split(',')]
    repeats = int(os.environ.get('PLANSECTION_BENCH_REPEATS','1'))
    modes = [x.strip() for x in os.environ.get('PLANSECTION_BENCH_MODES','Keep').split(',')]
    if repeats < 1 or any(x not in ('Keep','Omit') for x in modes):
        raise ValueError('Invalid benchmark repeats/modes')
    if any(not (0. < x < float('inf')) for x in tolerances):
        raise ValueError('Invalid benchmark tolerance')
    modules = [('current',current,os.path.join(ROOT,'PlanSection.py'))]
    if baseline:
        modules.insert(0,('baseline',imp.load_source('PlanSectionBenchmarkBaseline',baseline),baseline))
    for value in os.environ.get('PLANSECTION_BENCH_HLD_TOLERANCES','').split(','):
        if not value.strip(): continue
        accuracy = float(value)
        if not 0. < accuracy < float('inf'): raise ValueError('Invalid HLD tolerance')
        code_path = os.path.join(ROOT,'PlanSection.py')
        with open(code_path,'rb') as stream: source = stream.read().decode('utf-8-sig')
        needle = 'parameters.AbsoluteTolerance = tol'
        if source.count(needle)!=1: raise ValueError('HLD experiment no longer matches current source')
        expression = 'parameters.AbsoluteTolerance = min(tol, {0!r}*R.RhinoMath.UnitScale(R.UnitSystem.Millimeters, doc.ModelUnitSystem))'.format(accuracy)
        variant = imp.new_module('PlanSectionHldExperiment'+str(accuracy))
        variant.__file__ = code_path
        patched_source = source.replace(needle,expression).encode('utf-8')
        exec(compile(patched_source,code_path,'exec'),variant.__dict__)
        variant.benchmark_source_sha256 = hashlib.sha256(patched_source).hexdigest()
        variant.benchmark_hld_tolerance_mm = accuracy
        modules.append(('hld-'+str(accuracy)+'mm',variant,code_path))
    sources = [path]+([clipping] if clipping else [])
    report = dict(passed=False, rhino=str(R.RhinoApp.Version),
                  model=path, clipping=clipping, files_before=[sha(p) for p in sources],
                  code_sha256=dict((name,sha(code)) for name,module,code in modules),
                  in_memory_code_sha256=dict((name,module.benchmark_source_sha256)
                      for name,module,code in modules if hasattr(module,'benchmark_source_sha256')),
                  diagnostics_outside_timer=True, samples=[], input_source='saved real model',
                  batch_timing_scope='Cache setup + generate calls + cache disposal; excludes model load, diagnostics, output disposal, bake/export.',
                  passed_means='Valid execution and unchanged inputs; not output equivalence')
    output = os.path.join(out,'performance.json')
    doc, timers = None, []
    try:
        doc = R.RhinoDoc.OpenHeadless(path)
        if doc is None:
            raise IOError('Cannot open benchmark model')
        if clipping:
            attach_clippings(doc,clipping)
        before = fingerprint(doc)
        planes = dict((cp.Name,cp) for cp in current.clipping_planes(doc))
        missing = set(cases)-set(planes)
        if missing:
            raise ValueError('Missing clippings: '+', '.join(sorted(missing)))
        mm = R.RhinoMath.UnitScale(R.UnitSystem.Millimeters,doc.ModelUnitSystem)
        report['units'] = str(doc.ModelUnitSystem)
        timer_map = {}
        for name,module,code in modules:
            timer = Timings(module)
            timers.append(timer)
            timer_map[name] = timer
        report['batches'] = []
        for tolerance in tolerances:
            doc.ModelAbsoluteTolerance = tolerance*mm
            doc.ModelAngleToleranceRadians = math.radians(.5)
            for repeat in range(repeats):
                order = modules if repeat % 2 == 0 else list(reversed(modules))
                for name,module,code in order:
                    timer = timer_map[name]
                    for mode in modes:
                        batch = dict(version=name,repeat=repeat,mode=mode,document_tolerance_mm=tolerance)
                        if hasattr(module,'benchmark_hld_tolerance_mm'):
                            cap = module.benchmark_hld_tolerance_mm
                            batch['hld_tolerance_cap_mm'] = cap
                            batch['hld_tolerance_mm'] = min(doc.ModelAbsoluteTolerance,cap*mm)/mm
                        started = clock()
                        cache_type = getattr(module,'ModelCache',None)
                        cache = cache_type(doc) if cache_type is not None and len(cases)>1 else None
                        batch['cache_setup_seconds'] = clock()-started
                        first_sample = len(report['samples'])
                        try:
                            for case in cases:
                                entry = dict(batch,case=case,angle_degrees=.5)
                                drawing = None
                                timer.reset()
                                state = (doc.Modified,doc.ModelAbsoluteTolerance,doc.ModelAngleToleranceRadians,doc.ModelUnitSystem)
                                def progress(stage):
                                    entry['last_stage'] = stage
                                System.Console.WriteLine('BENCH '+json.dumps(entry))
                                try:
                                    kwargs = dict(small_details=mode=='Keep',progress=progress)
                                    if cache is not None and 'model_cache' in timer.options:
                                        kwargs['model_cache'] = cache
                                    native_profile = {}
                                    if 'profile' in timer.options:
                                        kwargs['profile'] = native_profile
                                    started = clock()
                                    try:
                                        drawing = module.generate(doc,planes[case],**kwargs)
                                    finally:
                                        entry['generate_seconds'] = clock()-started
                                        entry['stages'] = timer.rows
                                        entry['native_profile'] = native_profile
                                    entry['report'] = drawing['report']
                                    entry['geometry'] = metrics(drawing,doc)
                                    assert state == (doc.Modified,doc.ModelAbsoluteTolerance,doc.ModelAngleToleranceRadians,doc.ModelUnitSystem), 'Input document state changed'
                                    entry['passed'] = True
                                except Exception:
                                    entry.update(passed=False,error=traceback.format_exc())
                                finally:
                                    if drawing is not None:
                                        for item in drawing['objects']:
                                            item['geometry'].Dispose()
                                    report['samples'].append(entry)
                                    with open(output,'w') as stream:
                                        json.dump(report,stream,indent=2)
                                    System.Console.WriteLine('BENCH_RESULT '+json.dumps(dict((k,v) for k,v in entry.items() if k!='geometry')))
                        finally:
                            if cache is not None:
                                batch['cache_entries'] = len(cache.entries)
                                batch['cache_prepared'] = sum(e['geometry'] is not None for e in cache.entries.values())
                            started = clock()
                            if cache is not None: cache.Dispose()
                            batch['cache_dispose_seconds'] = clock()-started
                            batch['batch_seconds'] = (batch['cache_setup_seconds']+batch['cache_dispose_seconds']+
                                sum(e.get('generate_seconds',0.) for e in report['samples'][first_sample:]))
                            batch['passed'] = all(e.get('passed',False) for e in report['samples'][first_sample:])
                            report['batches'].append(batch)
                            System.Console.WriteLine('BENCH_BATCH '+json.dumps(batch))
        report['source_unchanged'] = fingerprint(doc)==before
        report['files_after'] = [sha(p) for p in sources]
        report['code_unchanged'] = report['code_sha256']==dict((name,sha(code)) for name,module,code in modules)
        report['passed'] = (report['source_unchanged'] and report['files_before']==report['files_after']
                            and report['code_unchanged'] and all(x['passed'] for x in report['samples']))
        if not report['passed']:
            raise RuntimeError('Benchmark failed: '+output)
        System.Console.WriteLine('PERFORMANCE_PASS '+output)
    except Exception:
        report.update(passed=False,error=traceback.format_exc())
        raise
    finally:
        for timer in timers:
            timer.close()
        if doc is not None:
            doc.Dispose()
        with open(output,'w') as stream:
            json.dump(report,stream,indent=2)


if __name__ == '__main__':
    run()
