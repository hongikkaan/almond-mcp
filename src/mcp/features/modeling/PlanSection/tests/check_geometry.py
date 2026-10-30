# -*- coding: utf-8 -*-
"""Native raw-section equivalence check; place beside benchmark_performance.py.

Required: PLANSECTION_BENCH_BASELINE (saved baseline PlanSection.py).
Optional: PLANSECTION_MODEL, PLANSECTION_CLIPPING, PLANSECTION_CASES (3F,Sec-D),
PLANSECTION_DOC_TOLERANCE_MM (0.5), PLANSECTION_TEST_OUTPUT.
No HLD, dedup, bake, save, or synthetic model generation is performed.
"""
import imp, json, math, os, sys, tempfile, traceback
import clr
import Rhino as R
import System

sys.path.insert(0, os.path.dirname(__file__))
import benchmark_performance as support
current, G = support.current, R.Geometry


class DifferentGeometry(Exception):
    pass


def maximum_distance(a, b, tolerance):
    if a.IsClosed != b.IsClosed:
        raise DifferentGeometry('Open/closed curve classification changed')
    if G.GeometryBase.GeometryEquals(a,b):
        return 0.0, 0.0
    values = []
    for first, second in ((a,b),(b,a)):
        result = G.Curve.GetDistancesBetweenCurves(first, second, tolerance*.1)
        if not result[0] or math.isnan(result[1]) or math.isinf(result[1]):
            raise DifferentGeometry('Native curve distance failed: {0}/{1}, lengths {2:g}/{3:g}, result {4}'.format(
                first.GetType().Name,second.GetType().Name,first.GetLength(),second.GetLength(),result))
        values.append(result[1])
    distance = max(values)
    if distance > tolerance:
        raise DifferentGeometry('Boundary deviation {0:g} exceeds {1:g}'.format(distance,tolerance))
    return distance, 0.0


def match_geometry(left, right, tolerance, compare):
    """One-to-one matching; order, orientation and curve domains may differ."""
    if len(left) != len(right):
        raise DifferentGeometry('Boundary/object count changed: {0} -> {1}'.format(len(left),len(right)))
    boxes = [g.GetBoundingBox(True) for g in right]
    tree, remaining, rows = G.RTree(), set(range(len(right))), []
    try:
        for i, box in enumerate(boxes): tree.Insert(box,i)
        for geometry in left:
            box = geometry.GetBoundingBox(True)
            query = G.BoundingBox(box.Min,box.Max)
            query.Inflate(tolerance)
            hits = []
            tree.Search(query,lambda sender,args:hits.append(args.Id))
            candidates = []
            for j in hits:
                if j not in remaining: continue
                other = boxes[j]
                if any(abs(getattr(p,axis)-getattr(q,axis)) > tolerance
                       for p,q in ((box.Min,other.Min),(box.Max,other.Max))
                       for axis in ('X','Y','Z')): continue
                candidates.append(j)
            rows.append((len(candidates),geometry,sorted(candidates)))
        results = []
        for count, geometry, candidates in sorted(rows,key=lambda row:row[0]):
            best = None
            reason = 'No corresponding boundary within the comparison tolerance'
            for j in candidates:
                if j not in remaining: continue
                try:
                    score = compare(geometry,right[j],tolerance)
                except DifferentGeometry as error:
                    reason = str(error)
                    continue
                if best is None or score < best[0]: best = (score,j)
                if score == (0.0,0.0): break
            if best is None: raise DifferentGeometry(reason)
            remaining.remove(best[1])
            results.append(best[0])
        return results
    finally:
        tree.Dispose()


def section_curves(items):
    """Keep closed loops separate; only join numerical-endpoint open fragments."""
    curves = [item['geometry'] for item in items]
    closed = [curve for curve in curves if curve.IsClosed]
    opened = [curve for curve in curves if not curve.IsClosed]
    if not opened: return closed, []
    mapping = clr.Reference[System.Array[System.Int32]]()
    joined = list(G.Curve.JoinCurves(opened,R.RhinoMath.ZeroTolerance,False,mapping) or [])
    if mapping.Value is None or len(mapping.Value) != len(opened) or any(k<0 for k in mapping.Value):
        for curve in joined: curve.Dispose()
        raise DifferentGeometry('Open-fragment normalization lost an input; equivalence is not established')
    return closed+joined, joined


def hatch_distance(a, b, tolerance):
    loops, measures, distances = [], [], []
    try:
        for outer in (True,False):
            left, right = list(a.Get3dCurves(outer) or []), list(b.Get3dCurves(outer) or [])
            loops.extend(left+right)
            if any(not c.IsValid or not c.IsClosed for c in left+right):
                raise RuntimeError('Invalid/open hatch boundary')
            distances.extend(match_geometry(left,right,tolerance,maximum_distance))
        for hatch in (a,b):
            value = G.AreaMassProperties.Compute(hatch)
            if value is None: raise RuntimeError('Cannot measure hatch area')
            measures.append(value)
        difference = abs(measures[0].Area-measures[1].Area)
        # Boundary correspondence above prevents equal-total-area false positives.
        limit = tolerance*sum(c.GetLength() for c in loops)*.5
        limit += measures[0].AreaError+measures[1].AreaError
        if difference > limit:
            raise DifferentGeometry('Hatch area difference {0:g} exceeds {1:g}'.format(difference,limit))
        return max([row[0] for row in distances] or [0.0]), difference
    finally:
        for curve in loops: curve.Dispose()
        for measure in measures: measure.Dispose()


def group_items(items):
    groups = {}
    for item in items:
        if not item['geometry'].IsValid: raise RuntimeError('Invalid raw section output')
        attrs = item['attributes']
        key = (item['role'],attrs.LayerIndex,attrs.GetUserString('ps:style') or '')
        groups.setdefault(key,[]).append(item)
    return groups


def compare_sections(before, after, tolerance):
    left, right = group_items(before), group_items(after)
    if set(left) != set(right): raise DifferentGeometry('Role/layer/source-style groups changed')
    rows = []
    for key in sorted(left):
        owned = []
        try:
            if key[0] == 'section':
                a, extra = section_curves(left[key]); owned.extend(extra)
                b, extra = section_curves(right[key]); owned.extend(extra)
                values = match_geometry(a,b,tolerance,maximum_distance)
            elif key[0] == 'hatch':
                a = [item['geometry'] for item in left[key]]
                b = [item['geometry'] for item in right[key]]
                values = match_geometry(a,b,tolerance,hatch_distance)
            else:
                raise RuntimeError('Unexpected raw sections role: '+str(key[0]))
            rows.append(dict(role=key[0],layer_index=key[1],style=key[2],
                             baseline_count=len(left[key]),current_count=len(right[key]),
                             compared_count=len(a),max_distance=max([v[0] for v in values] or [0.0]),
                             max_hatch_area_difference=max([v[1] for v in values] or [0.0])))
        except DifferentGeometry as error:
            raise DifferentGeometry('{0}/layer {1}: {2}'.format(key[0],key[1],error))
        finally:
            for curve in owned: curve.Dispose()
    return rows


def run():
    baseline_path = os.environ['PLANSECTION_BENCH_BASELINE']
    baseline = imp.load_source('PlanSectionGeometryBaseline',baseline_path)
    path = os.environ.get('PLANSECTION_MODEL') or os.path.join(support.ROOT,'TEST.3dm')
    clipping = os.environ.get('PLANSECTION_CLIPPING')
    cases = [s.strip() for s in os.environ.get('PLANSECTION_CASES','3F,Sec-D').split(',')]
    out = os.environ.get('PLANSECTION_TEST_OUTPUT') or os.path.join(tempfile.gettempdir(),'PlanSection-checks')
    if not os.path.isdir(out): os.makedirs(out)
    output = os.path.join(out,'geometry-comparison.json')
    report = dict(passed=False,rhino=str(R.RhinoApp.Version),model=path,clipping=clipping,cases=[],
                  baseline_sha256=support.sha(baseline_path),
                  current_sha256=support.sha(os.path.join(support.ROOT,'PlanSection.py')),
                  scope='raw sections on identical prepared records; no post-dedup equality claim')
    sources = [path]+([clipping] if clipping else [])
    report['files_before'] = [support.sha(p) for p in sources]
    doc = None
    try:
        doc = R.RhinoDoc.OpenHeadless(path)
        if doc is None: raise IOError('Cannot open model')
        if clipping: support.attach_clippings(doc,clipping)
        mm = R.RhinoMath.UnitScale(R.UnitSystem.Millimeters,doc.ModelUnitSystem)
        doc.ModelAbsoluteTolerance = float(os.environ.get('PLANSECTION_DOC_TOLERANCE_MM','0.5'))*mm
        doc.ModelAngleToleranceRadians = math.radians(.5)
        tolerance = current.section_tolerance(doc)
        fingerprint = support.fingerprint(doc)
        state = (doc.Modified,doc.ModelUnitSystem,doc.ModelAbsoluteTolerance,doc.ModelAngleToleranceRadians)
        report.update(units=str(doc.ModelUnitSystem),document_tolerance=doc.ModelAbsoluteTolerance,
                      comparison_tolerance=tolerance,distance_solver_tolerance=tolerance*.1)
        planes = dict((cp.Name,cp) for cp in current.clipping_planes(doc))
        for name in cases:
            row, records, before, after = dict(name=name,passed=False), [], [], []
            try:
                clip = current.read_clip(doc,planes[name]); clip['elevation'] = False
                records = current.model_objects(doc,clip,{})
                crc = [r['geometry'].DataCRC(0) for r in records]
                before = baseline.sections(doc,records,clip['plane'],True)
                assert crc == [r['geometry'].DataCRC(0) for r in records], 'Baseline changed prepared inputs'
                after = current.sections(doc,records,clip['plane'],True)
                assert crc == [r['geometry'].DataCRC(0) for r in records], 'Current changed prepared inputs'
                row['groups'] = compare_sections(before,after,tolerance)
                row.update(passed=True,sources=len(records))
            except Exception:
                row['error'] = traceback.format_exc()
            finally:
                for item in before+after: item['geometry'].Dispose()
                for record in records: record['geometry'].Dispose()
                report['cases'].append(row)
                System.Console.WriteLine('GEOMETRY_RESULT '+json.dumps(row))
                with open(output,'w') as stream: json.dump(report,stream,indent=2)
        report['files_after'] = [support.sha(p) for p in sources]
        report['source_unchanged'] = (support.fingerprint(doc)==fingerprint and
            state==(doc.Modified,doc.ModelUnitSystem,doc.ModelAbsoluteTolerance,doc.ModelAngleToleranceRadians))
        assert report['source_unchanged'] and report['files_before']==report['files_after'], 'Input changed'
        assert report['current_sha256']==support.sha(os.path.join(support.ROOT,'PlanSection.py')), 'Code changed during check'
        report['passed'] = bool(report['cases']) and all(row['passed'] for row in report['cases'])
        if not report['passed']: raise RuntimeError('Raw-section comparison failed: '+output)
        System.Console.WriteLine('GEOMETRY_PASS '+output)
    except Exception:
        report.update(passed=False,error=traceback.format_exc())
        raise
    finally:
        if doc is not None: doc.Dispose()
        with open(output,'w') as stream: json.dump(report,stream,indent=2)


if __name__ == '__main__':
    run()
