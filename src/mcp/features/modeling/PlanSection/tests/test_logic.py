"""Model-free contracts. API doubles cannot validate Rhino's native geometry."""
import contextlib
import importlib.util
import io
import math
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
with patch.dict(sys.modules, {name: MagicMock() for name in
        ['clr','Rhino','System','System.Drawing','System.Collections.Generic']}):
    spec = importlib.util.spec_from_file_location('plansection_logic', ROOT / 'PlanSection.py')
    ps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ps)


class Attributes:
    def __init__(self, values=None, layer=0):
        self.values, self.LayerIndex = dict(values or {}), layer
    def GetUserString(self, key): return self.values.get(key)
    def SetUserString(self, key, value): self.values[key] = value
    def DeleteAllUserStrings(self): self.values.clear()
    def Duplicate(self): return Attributes(self.values, self.LayerIndex)


def clipping(reference=False, values=None):
    geo = NS(Plane=NS(IsValid=True), PlaneDepthEnabled=False, PlaneDepth=10,
             ParticipationListsEnabled=True, GetClipParticipation=lambda: (['source'],[0],False))
    return NS(Id='clip',Name='Plan',IsReference=reference,
              Attributes=Attributes(values),ClippingPlaneGeometry=geo)


class OptionsAndMetadata(unittest.TestCase):
    def test_style_limits_and_distance_clamping(self):
        ps.validate_options(.09,.04,80,45)
        for values in [(0,.04,80,45),(.04,.09,80,45),(.09,.04,40,45),
                       (.09,.04,101,45),(.09,.04,80,-1),(.09,.04,math.nan,45),
                       (math.inf,.04,80,45)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                ps.validate_options(*values)
        self.assertEqual(ps.relative_style(-5,0,10,.09,.04,80,45),(.09,51))
        self.assertEqual(ps.relative_style(20,0,10,.09,.04,80,45),(.04,140))
        self.assertEqual(ps.relative_style(5,5,5,.09,.04,80,45),(.09,51))

    def test_pdf_defaults_and_invalid_values(self):
        self.assertEqual(ps.pdf_settings(clipping()),([210.,297.],300.))
        for values in [{'Paper':'0*297'},{'Paper':'nan*2'},{'Paper':'1*2*3'},
                       {'Scale':'0'},{'Scale':'inf'},{'Scale':'bad'}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                ps.pdf_settings(clipping(values=values))

    def test_saved_placement_prefers_output_then_clipping(self):
        cp = clipping(values={'draft_plane':'shared'})
        with patch.object(ps,'draft_plane',side_effect=lambda value:value):
            self.assertEqual(ps.saved_placement(cp,[]),'shared')
            self.assertEqual(ps.saved_placement(cp,[NS(Attributes=Attributes())]),'shared')
            self.assertEqual(ps.saved_placement(cp,[NS(Attributes=Attributes({'ps:placement':'local'}))]),'local')
            with self.assertRaisesRegex(ValueError,'inconsistent placement'):
                ps.saved_placement(cp,[NS(Attributes=Attributes({'ps:placement':v})) for v in ['a','b']])

    def test_output_user_text_allowlist_does_not_edit_input(self):
        values = {'ps:source_layer':'Model','ps:placement':'local','ps:sources':'internal','note':'old'}
        source = Attributes(values)
        self.assertEqual(ps.output_attributes(source).values,{'ps:source_layer':'Model','ps:placement':'local'})
        self.assertEqual(source.values,values)

    def test_read_clip_shared_default_and_explicit_update_target(self):
        shared, moved = NS(IsValid=True), NS(IsValid=True)
        doc = NS(Objects=NS(FindId=Mock(return_value=None)),Layers=NS(Count=0))
        cp = clipping(True,{'draft_plane':'shared'})
        with patch.object(ps,'draft_plane',return_value=shared) as draft:
            result = ps.read_clip(doc,cp)
            self.assertIs(result['target'],shared)
            self.assertFalse(result['enabled'])
            doc.Objects.FindId.assert_not_called()
            draft.assert_called_once_with('shared')
            self.assertIs(ps.read_clip(doc,cp,moved)['target'],moved)

    def test_local_participation_rejects_stale_ids(self):
        doc = NS(Objects=NS(FindId=lambda value:None),Layers=NS(Count=0))
        with self.assertRaisesRegex(ValueError,'missing object'):
            ps.read_clip(doc,clipping())

    def test_invalid_depth_and_target_are_rejected(self):
        cp = clipping(True)
        for value in [-1,math.nan,math.inf]:
            cp.ClippingPlaneGeometry.PlaneDepthEnabled = True
            cp.ClippingPlaneGeometry.PlaneDepth = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError,'depth'):
                ps.read_clip(NS(),cp)
        cp.ClippingPlaneGeometry.PlaneDepthEnabled = False
        with self.assertRaisesRegex(ValueError,'placement'):
            ps.read_clip(NS(),cp,NS(IsValid=False))


class SourceScope(unittest.TestCase):
    def test_enumerator_includes_hidden_locked_reference_but_not_definitions(self):
        settings = NS()
        doc = NS(Objects=NS(GetObjectList=Mock(return_value=['a'])))
        with patch.object(ps,'D',NS(ObjectEnumeratorSettings=lambda:settings)):
            self.assertEqual(ps.objects(doc),['a'])
        self.assertTrue(all(getattr(settings,name) for name in
                            ['NormalObjects','HiddenObjects','LockedObjects','ReferenceObjects']))
        self.assertFalse(settings.DeletedObjects)
        self.assertFalse(settings.IdefObjects)

    def test_clipping_includes_all_layers_references_and_sorts_names(self):
        class Clip:
            def __init__(self,name,index,reference=False):
                self.Id = self.Name = name
                self.IsReference,self.Attributes = reference,Attributes(layer=index)
        rows = [Clip('3F',0),Clip('Sec-D',1,True),Clip('WrongPrefix',1),Clip('Child',2)]
        doc = NS(Layers=[NS(FullPath=name) for name in ['setting::Clipping::Section',
                    'attach::setting::clipping::Section','setting::clipping::Section::child']])
        with patch.object(ps,'D',NS(ClippingPlaneObject=Clip)),patch.object(ps,'objects',return_value=rows):
            self.assertEqual([o.Name for o in ps.clipping_planes(doc)],['WrongPrefix','Sec-D','Child','3F'])

    def test_only_active_roots_but_including_nested_reference_members(self):
        class Transform:
            def __mul__(self,other): return self
        class Brep:
            IsValid = True
            def GetBoundingBox(self,accurate):
                return NS(Transform=lambda value:None,GetCorners=lambda:[0.,1.])
            def Duplicate(self): return Brep()
            def Transform(self,value): return True
        class Instance: pass
        def leaf(name,reference=False):
            return NS(Id=name,Attributes=Attributes(),Geometry=Brep(),IsReference=reference,
                      IsHidden=True,IsLocked=True)
        instance = Instance()
        instance.Id,instance.Attributes,instance.IsReference = 'active-block',Attributes(),False
        instance.InstanceXform = Transform()
        instance.InstanceDefinition = NS(Id='definition',GetObjects=lambda:[leaf('member',True)])
        active, foreign = leaf('active'), leaf('attached',True)
        foreign.Geometry = None  # Reference exclusion must happen before geometry access.
        unused = type('UnusedGeometry',(),{})
        geo = NS(Brep=Brep,Surface=unused,Extrusion=unused,SubD=unused,Mesh=unused,
                 ClippingPlaneSurface=unused,Transform=NS(Identity=Transform()))
        clip = dict(ids=set(),layers=set(),enabled=False,exclude=False,
                    plane=NS(DistanceTo=lambda point:point),depth=None)
        with patch.object(ps,'G',geo),patch.object(ps,'D',NS(InstanceObject=Instance)), \
             patch.object(ps,'objects',return_value=[active,foreign,instance]), \
             patch.object(ps,'resolved_attributes',return_value='style'):
            result = ps.model_objects(NS(ModelAbsoluteTolerance=.01),clip,{})
        self.assertEqual([r['source'] for r in result],['active','active-block/member'])
        self.assertIsNot(result[0]['geometry'],active.Geometry)


class CurveContracts(unittest.TestCase):
    def test_simple_closed_loop_avoids_boolean_reconstruction(self):
        curve = NS(IsValid=True,IsClosed=True,IsInPlane=lambda plane,tol:True)
        area = NS(Area=10.,AreaError=1e-9,Dispose=Mock())
        geo = NS(Curve=NS(CreateBooleanRegions=Mock()),
                 AreaMassProperties=NS(Compute=Mock(return_value=area)),
                 Intersect=NS(Intersection=NS(CurveSelf=lambda *args:[])))
        with patch.object(ps,'G',geo):
            self.assertEqual(ps.clean_closed_curve(curve,'plane',.01,.01),([curve],[]))
        geo.Curve.CreateBooleanRegions.assert_not_called()
        area.Dispose.assert_called_once()

    def test_uncertain_area_still_requires_topology(self):
        curve = NS(IsValid=True,IsClosed=True,IsInPlane=lambda plane,tol:True,
                   TryGetPolyline=lambda:(False,None))
        area = NS(Area=0.,AreaError=0.,Dispose=Mock())
        regions = NS(RegionCount=0,Dispose=Mock())
        geo = NS(Curve=NS(CreateBooleanRegions=Mock(return_value=regions)),
                 AreaMassProperties=NS(Compute=lambda *args:area),
                 Intersect=NS(Intersection=NS(CurveSelf=lambda *args:[])))
        with patch.object(ps,'G',geo),self.assertRaisesRegex(ValueError,'returned no region'):
            ps.clean_closed_curve(curve,'plane',.01,.01)
        self.assertEqual(geo.Curve.CreateBooleanRegions.call_count,2)
        area.Dispose.assert_called_once()

    def test_empty_boolean_retains_only_proven_collinear_retraces(self):
        start = NS(DistanceTo=lambda point:point.distance,distance=0,deviation=0)
        end = NS(distance=1,deviation=0)
        regions = NS(RegionCount=0,Dispose=Mock())
        axis = NS(IsValid=True,DistanceTo=lambda point,limit:point.deviation)
        geo = NS(Curve=NS(CreateBooleanRegions=lambda *args:regions),Line=lambda *args:axis)
        curve = NS(IsValid=False,TryGetPolyline=lambda:(True,[start,end,start]))
        with patch.object(ps,'G',geo),patch.object(ps,'R',NS(RhinoMath=NS(ZeroTolerance=1e-12))):
            self.assertEqual(ps.clean_closed_curve(curve,'plane',.01,.01),([],[curve]))
            end.deviation = .001
            with self.assertRaisesRegex(ValueError,'returned no region'):
                ps.clean_closed_curve(curve,'plane',.01,.01)

    def test_empty_boolean_does_not_treat_cancelled_area_as_no_area(self):
        regions = NS(RegionCount=0,Dispose=Mock())
        geo = NS(Curve=NS(CreateBooleanRegions=Mock(return_value=regions)),
                 AreaMassProperties=NS(Compute=Mock(return_value=NS(Area=0,AreaError=0,Dispose=Mock()))))
        curve = NS(IsValid=False,TryGetPolyline=lambda:(False,None))
        with patch.object(ps,'G',geo),self.assertRaisesRegex(ValueError,'returned no region'):
            ps.clean_closed_curve(curve,'plane',.01,.01)
        geo.AreaMassProperties.Compute.assert_not_called()
        self.assertEqual(geo.Curve.CreateBooleanRegions.call_count,2)

    def test_closed_seam_uses_trim_and_split_uses_only_interior_parameters(self):
        event = NS(IsPoint=True,ParameterA=0,ParameterB=2,IsOverlap=False)
        piece = NS(IsClosed=True,IsValid=True,Simplify=lambda *args:None)
        curve = NS(IsClosed=True,Domain=NS(T0=0,T1=4),Trim=Mock(return_value=piece),
                   Split=Mock(return_value=[piece]))
        geo = NS(Intersect=NS(Intersection=NS(CurveSelf=lambda *args:[event])),
                 CurveSimplifyOptions=NS(All='all'))
        with patch.object(ps,'G',geo):
            parts,split,overlap = ps.split_crossings(curve,.01,.01)
            self.assertEqual(len(parts),2)
            self.assertTrue(split)
            curve.Split.assert_not_called()
            self.assertEqual([call.args for call in curve.Trim.call_args_list],[(0,2),(2,4)])
            curve.IsClosed = False
            ps.split_crossings(curve,.01,.01)
            curve.Split.assert_called_once_with([2])

    def test_failed_seam_trim_is_reported(self):
        curve = NS(IsClosed=True,Domain=NS(T0=0,T1=4),Trim=lambda *args:None)
        event = NS(IsPoint=True,ParameterA=0,ParameterB=2)
        geo = NS(Intersect=NS(Intersection=NS(CurveSelf=lambda *args:[event])))
        with patch.object(ps,'G',geo),self.assertRaisesRegex(ValueError,'trim failed'):
            ps.split_crossings(curve,.01,.01)


class OverlapContracts(unittest.TestCase):
    def test_section_tolerance_tracks_physical_units(self):
        for scale,document,expected in [(1.,.5,.01),(1.,1.,.01),(1.,.005,.005),(.001,.0005,.00001)]:
            rhino = NS(RhinoMath=NS(UnitScale=lambda *args:scale),UnitSystem=NS(Millimeters='mm'))
            with self.subTest(scale=scale,document=document),patch.object(ps,'R',rhino):
                self.assertAlmostEqual(ps.section_tolerance(NS(ModelAbsoluteTolerance=document,
                                                              ModelUnitSystem='model')),expected)

    def test_thin_sections_survive_and_overlap_keeps_section_priority(self):
        class Line:
            def __init__(self,start,end,y=0.):
                self.Domain,self.y = NS(T0=start,T1=end),y
            def GetBoundingBox(self,accurate): return NS(Inflate=lambda tol:None)
            def Trim(self,start,end): return Line(start,end,self.y)
            def IsShort(self,tol): return self.Domain.T1-self.Domain.T0<=tol
        class Tree:
            def __init__(self): self.ids = []
            def Insert(self,box,index): self.ids.append(index)
            def Search(self,box,callback):
                for index in self.ids: callback(None,NS(Id=index))
            def Dispose(self): pass
        tolerances = []
        def overlap(a,b,tol,overlap_tol):
            tolerances.append(tol)
            start,end = max(a.Domain.T0,b.Domain.T0),min(a.Domain.T1,b.Domain.T1)
            if abs(a.y-b.y)<=tol and start<end:
                return [NS(IsOverlap=True,OverlapA=NS(T0=start,T1=end))]
            return []
        geo = NS(Curve=Line,RTree=Tree,Intersect=NS(Intersection=NS(CurveCurve=overlap)))
        attrs = Attributes({'ps:style':'same'})
        for document_tol in (.5,1.):
            first = Line(0.,10.)
            rows = [('section',first),('section',Line(0.,10.,.1)),
                    ('section',Line(5.,15.)),('section',Line(20.,20.2)),
                    ('elevation',Line(0.,10.,.1)),('elevation',Line(30.,30.2))]
            items = [dict(geometry=line,attributes=attrs,role=role) for role,line in rows]
            with self.subTest(tolerance=document_tol),patch.object(ps,'G',geo), \
                 patch.object(ps,'R',NS(RhinoMath=NS(ZeroTolerance=1e-12))):
                result = ps.deduplicate(items,document_tol,.01)
            sections = [x['geometry'] for x in result if x['role']=='section']
            elevations = [x['geometry'] for x in result if x['role']=='elevation']
            self.assertEqual(len(sections),4)
            self.assertEqual(len(elevations),1)
            self.assertIs(sections[0],first)
            self.assertAlmostEqual(sum(c.Domain.T1-c.Domain.T0 for c in sections),25.2)
            self.assertEqual((elevations[0].Domain.T0,elevations[0].Domain.T1),(30.,30.2))
        self.assertIn(.01,tolerances)
        self.assertIn(.5,tolerances)
        self.assertIn(1.,tolerances)


class SectionStyleGroups(unittest.TestCase):
    def check_optional_style(self, custom_field):
        color = NS(ToArgb=lambda: 0)
        styles = []
        for crc in (None, 0, 7):
            custom = None if crc is None else NS(DataCRC=lambda seed, value=crc: value)
            attrs = NS(LayerIndex=0, ObjectColor=color, PlotColor=color,
                       PlotWeight=.1, LinetypeIndex=0, LinetypePatternScale=1.,
                       GetCustomSectionStyle=lambda: None, GetCustomLinetype=lambda: None)
            setattr(attrs, custom_field, lambda value=custom: value)
            attrs.Duplicate = lambda value=attrs: value
            styles.append(attrs)
        # Reverse input order and repeat one style: sorting must not collapse
        # absent custom styles into CRC 0, or union different applied styles.
        records = [dict(geometry=NS(), resolved=styles[i], source=str(n))
                   for n, i in enumerate((2, 1, 0, 1))]
        curve = NS(IsClosed=False)
        metadata = Mock(return_value='metadata')
        geo = NS(Mesh=type('Mesh', (), {}), Brep=type('Brep', (), {}))
        with patch.object(ps, 'G', geo), \
             patch.object(ps, 'section_tolerance', return_value=.01), \
             patch.object(ps, 'record_bounds', return_value=None), \
             patch.object(ps, 'meets_plane', return_value=True), \
             patch.object(ps, 'intersect', return_value=[curve]), \
             patch.object(ps, 'planar_union', return_value=[]), \
             patch.object(ps, 'split_crossings', return_value=([curve], [])), \
             patch.object(ps, 'drawing_metadata', metadata), \
             patch.object(ps, 'drawing_attributes', side_effect=lambda doc, attrs, *args: attrs):
            result = ps.sections(NS(ModelAngleToleranceRadians=.01), records, 'plane', False)
        self.assertEqual([item['attributes'] for item in result],
                         [styles[0], styles[1], styles[1], styles[2]])
        self.assertEqual([call.args[2] for call in metadata.call_args_list],
                         [['2'], ['1', '3'], ['0']])

    def test_absent_and_custom_section_styles_remain_separate(self):
        self.check_optional_style('GetCustomSectionStyle')

    def test_absent_and_custom_linetypes_remain_separate(self):
        self.check_optional_style('GetCustomLinetype')


class ElevationJoinInterop(unittest.TestCase):
    def cleanup(self, ironpython, mapping=(0, 0)):
        class Curve:
            IsValid = IsClosed = True
            def GetBoundingBox(self, plane):
                return NS(Diagonal=NS(Length=30.))
        joined = Curve()
        ref = NS(Value=None)
        int_array = object()
        clr_api = NS(Reference={int_array: lambda: ref}) if ironpython else NS()
        def join(curves, tolerance, preserve_direction, out_key):
            self.assertEqual(len(curves), 2)
            self.assertEqual(tolerance, .01)
            self.assertFalse(preserve_direction)
            if ironpython:
                self.assertIs(out_key, ref)
                ref.Value = mapping
                return [joined]
            # Python.NET has no clr.Reference. The fourth argument must select
            # the out-key overload instead of the three-argument Curve[] API.
            self.assertIsNone(out_key)
            return [joined], mapping
        Curve.JoinCurves = staticmethod(join)
        attrs = [Attributes({'ps:sources': '["' + name + '"]'}) for name in ('a', 'b')]
        items = [dict(geometry=Curve(), attributes=a, role='elevation') for a in attrs]
        rhino = NS(RhinoMath=NS(UnitScale=lambda *args: 1.), UnitSystem=NS(Millimeters=1))
        with patch.object(ps, 'clr', clr_api), \
             patch.object(ps, 'System', NS(Array={int: int_array}, Int32=int)), \
             patch.object(ps, 'R', rhino), patch.object(ps, 'G', NS(Curve=Curve)), \
             patch.object(ps, 'style_key', return_value='same'), \
             patch.object(ps, 'split_crossings', return_value=([joined], False, False)):
            return ps.cleanup_elevations(NS(ModelUnitSystem=1, ModelAbsoluteTolerance=.01,
                                           ModelAngleToleranceRadians=.01), items, 'plane')

    def test_pythonnet_tuple_and_ironpython_reference_preserve_contributors(self):
        for ironpython in (False, True):
            with self.subTest(ironpython=ironpython):
                result, report = self.cleanup(ironpython)
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]['attributes'].GetUserString('ps:sources'), '["a", "b"]')
                self.assertEqual((report['input'], report['joined']), (2, 1))

    def test_both_runtimes_reject_missing_or_lost_mapping(self):
        for ironpython in (False, True):
            for mapping in (None, [0], [0, -1]):
                with self.subTest(ironpython=ironpython, mapping=mapping), self.assertRaises(ValueError):
                    self.cleanup(ironpython, mapping)


class PlacementPreview(unittest.TestCase):
    def test_origin_marker_and_event_cleanup_on_accept_or_cancel(self):
        class Event:
            def __iadd__(self,handler): self.handler = handler; return self
            def __isub__(self,handler): self.handler = None; return self
        class Transform:
            def __mul__(self,point): return point+10
        target = NS(Origin=123)
        for accepted in (True,False):
            for previous in (None,100):
                with self.subTest(accepted=accepted,previous=previous):
                    getter,display = Mock(),Mock()
                    getter.DynamicDraw = Event()
                    def get():
                        getter.DynamicDraw.handler(None,NS(CurrentPoint='mouse',Display=display))
                        return 'point' if accepted else 'cancel'
                    getter.Get.side_effect = get
                    rhino = NS(Input=NS(Custom=NS(GetPoint=lambda:getter),GetResult=NS(Point='point')))
                    with patch.object(ps,'R',rhino), \
                         patch.object(ps,'G',NS(Transform=NS(Translation=lambda delta:Transform()))), \
                         patch.object(ps,'Color',NS(DodgerBlue='blue',White='white')), \
                         patch.object(ps,'drawing_frame',return_value=NS(Corner=lambda i:i)), \
                         patch.object(ps,'placement_plane',return_value=target), \
                         patch.object(ps,'drawing_transform',return_value=Transform()):
                        result = ps.pick_placement({},'cut','Plan',previous)
                    self.assertIs(result,target if accepted else None)
                    display.DrawDot.assert_called_once_with(123,'Clipping origin','blue','white')
                    display.DrawPolyline.assert_called_once_with([10,11,12,13,10],'blue',2)
                    getter.Dispose.assert_called_once()
                    self.assertIsNone(getter.DynamicDraw.handler)


class GeneratedOwnership(unittest.TestCase):
    @staticmethod
    def item():
        return dict(geometry=NS(Dispose=Mock()),attributes=Attributes(),role='section')

    def generate_with(self, section_items, deduplicated=None, cleaned=None, model_cache=None):
        source = NS(Dispose=Mock())
        records = [dict(geometry=source,attributes=Attributes(),resolved=Attributes())]
        replacements = dict(read_clip=Mock(return_value=dict(plane='cut',depth=None,target='target')),
            model_objects=Mock(return_value=records),sections=Mock(return_value=section_items),
            elevations=Mock(return_value=[]),section_tolerance=Mock(return_value=.01),
            deduplicate=Mock(side_effect=lambda items,*args: items if deduplicated is None else deduplicated),
            cleanup_elevations=Mock(side_effect=lambda doc,items,*args:
                                    (items if cleaned is None else cleaned,{})))
        with patch.multiple(ps,**replacements):
            result = ps.generate(NS(ModelAbsoluteTolerance=.5),clipping(),place=False,
                                 model_cache=model_cache)
        return result,source

    def test_dispose_difference_preserves_geometry_alias_and_disposes_once(self):
        retained,dropped = self.item(),self.item()
        ps.dispose_drawing_items([retained,dict(retained),dropped,dict(dropped)],[dict(retained)])
        retained['geometry'].Dispose.assert_not_called()
        dropped['geometry'].Dispose.assert_called_once()

    def test_generate_releases_dropped_and_replaced_outputs_not_retained_aliases(self):
        kept,dropped,untrimmed,trimmed,cleanup_drop = [self.item() for _ in range(5)]
        result,source = self.generate_with([kept,dropped,untrimmed,cleanup_drop],
            deduplicated=[dict(kept),trimmed,cleanup_drop],cleaned=[dict(kept),trimmed])
        self.assertEqual(len(result['objects']),2)
        for item in (dropped,untrimmed,cleanup_drop):
            item['geometry'].Dispose.assert_called_once()
        for item in (kept,trimmed):
            item['geometry'].Dispose.assert_not_called()
        source.Dispose.assert_called_once()

    def test_cancel_after_sections_releases_completed_outputs(self):
        for model_cache in (None,object()):
            item = self.item()
            source = NS(Dispose=Mock())
            records = [dict(geometry=source,attributes=Attributes(),resolved=Attributes())]
            def progress(stage):
                if stage=='elevation': raise RuntimeError('Cancelled after sections')
            with self.subTest(cached=model_cache is not None), \
                 patch.object(ps,'read_clip',return_value=dict(plane='cut',depth=None,target='target')), \
                 patch.object(ps,'model_objects',return_value=records), \
                 patch.object(ps,'sections',return_value=[item]), \
                 self.assertRaisesRegex(RuntimeError,'Cancelled after sections'):
                ps.generate(NS(ModelAbsoluteTolerance=.5),clipping(),place=False,
                            progress=progress,model_cache=model_cache)
            item['geometry'].Dispose.assert_called_once()
            if model_cache is None: source.Dispose.assert_called_once()
            else: source.Dispose.assert_not_called()

    def test_success_transfers_outputs_to_caller_and_preserves_cached_model(self):
        item = self.item()
        result,source = self.generate_with([item],model_cache=object())
        self.assertIs(result['objects'][0]['geometry'],item['geometry'])
        item['geometry'].Dispose.assert_not_called()
        source.Dispose.assert_not_called()
        ps.dispose_drawing_items(result['objects'])
        item['geometry'].Dispose.assert_called_once()


class Workflow(unittest.TestCase):
    def run_mode(self,mode,pick=False,cancel=False,fail=False,reference=False,fail_output=False):
        cp,other = clipping(reference),clipping()
        other.Id = 'other'
        drawing = dict(objects=[{'geometry':Mock()}],report={})
        saved,picked,world = object(),object(),object()
        options = dict(mode=mode,hatch=True,elevation=True,pick=pick,small_details=False,
                       near_width=.09,far_width=.04,near_dark=80,far_dark=45)
        doc = Mock()
        doc.CurrentUndoRecordSerialNumber = 0
        doc.BeginUndoRecord.return_value = 7
        rhino = NS(RhinoApp=NS(Wait=lambda:None,EscapeKeyPressed=MagicMock()))
        selected = [cp,other] if mode=='Update' else [cp]
        generate = Mock(return_value=drawing,side_effect=ValueError('injected failure') if fail else None)
        replacements = dict(clipping_planes=Mock(return_value=selected),
            select_clippings=Mock(side_effect=lambda value,caller:value),get_options=Mock(return_value=options),
            generate=generate,pick_placement=Mock(return_value=None if cancel else picked),
            move_drawing=Mock(),bake=Mock(return_value=[]),export_drawing=Mock(return_value='result'),
            export_pdf=Mock(return_value='result'),pdf_settings=Mock(return_value=([210,297],300)),
            plane_json=Mock(return_value='picked-plane'),
            drawing_objects=Mock(side_effect=lambda doc,cp:[object()] if cp.Id=='clip' else []),
            saved_placement=Mock(return_value=saved),reposition_drawing=Mock(return_value=True))
        events = Mock()
        for name in ('generate','pick_placement','move_drawing','bake','export_drawing','export_pdf'):
            events.attach_mock(replacements[name],name)
        if fail_output:
            for name in ('bake','export_drawing','export_pdf'):
                replacements[name].side_effect = ValueError('injected output failure')
        with patch.multiple(ps,**replacements),patch.object(ps,'R',rhino), \
             patch.object(ps,'G',NS(Plane=NS(WorldXY=world))), \
             patch.dict(sys.modules,{'rhinoscriptsyntax':NS(BrowseForFolder=lambda **kw:'output',
                 GetString=Mock(side_effect=['Project',{'Document':'Create','Files':'Create','Placement':'Move'}.get(mode,mode)]))}), \
             contextlib.redirect_stdout(io.StringIO()):
            ps.main(doc)
        return NS(**replacements,doc=doc,cp=cp,saved=saved,picked=picked,world=world,drawing=drawing,events=events)

    def test_generated_geometry_released_after_each_output(self):
        for mode in ('Document','Update','Files','PDF'):
            with self.subTest(mode=mode):
                run = self.run_mode(mode)
                run.drawing['objects'][0]['geometry'].Dispose.assert_called_once()

    def test_generated_geometry_released_after_output_failure(self):
        for mode in ('Document','Update','Files','PDF'):
            with self.subTest(mode=mode):
                run = self.run_mode(mode,fail_output=True)
                run.drawing['objects'][0]['geometry'].Dispose.assert_called_once()

    def test_update_uses_saved_target_skips_missing_and_never_picks(self):
        run = self.run_mode('Update',pick=True)
        run.generate.assert_called_once()
        self.assertIs(run.generate.call_args.args[4],run.saved)
        run.pick_placement.assert_not_called()
        run.bake.assert_called_once()
        run.doc.EndUndoRecord.assert_called_once_with(7)

    def test_document_without_pick_uses_default_selection(self):
        run = self.run_mode('Document')
        self.assertIsNone(run.generate.call_args.args[4])
        self.assertTrue(run.generate.call_args.kwargs['place'])
        self.assertFalse(run.generate.call_args.kwargs['small_details'])
        run.pick_placement.assert_not_called()

    def test_files_use_shared_default_without_baking(self):
        run = self.run_mode('Files')
        self.assertIsNone(run.generate.call_args.args[4])
        run.export_drawing.assert_called_once()
        run.bake.assert_not_called()
        run.doc.Objects.ModifyAttributes.assert_not_called()

    def test_successful_document_pick_moves_before_bake(self):
        run = self.run_mode('Document',pick=True)
        self.assertFalse(run.generate.call_args.kwargs['place'])
        run.move_drawing.assert_called_once_with(run.drawing,run.cp.ClippingPlaneGeometry.Plane,run.picked)
        run.bake.assert_called_once_with(run.doc,run.cp,run.drawing,run.picked)
        self.assertEqual([call[0] for call in run.events.mock_calls],
                         ['generate','pick_placement','move_drawing','bake'])

    def test_files_pick_saves_only_local_clipping_origin(self):
        for reference in (False,True):
            with self.subTest(reference=reference):
                run = self.run_mode('Files',pick=True,reference=reference)
                self.assertFalse(run.generate.call_args.kwargs['place'])
                run.move_drawing.assert_called_once_with(run.drawing,run.cp.ClippingPlaneGeometry.Plane,run.picked)
                run.export_drawing.assert_called_once()
                run.bake.assert_not_called()
                if reference:
                    run.doc.Objects.ModifyAttributes.assert_not_called()
                else:
                    args = run.doc.Objects.ModifyAttributes.call_args.args
                    self.assertEqual((args[0],args[1].GetUserString('draft_plane'),args[2]),('clip','picked-plane',True))

    def test_cancelled_placement_does_not_bake(self):
        run = self.run_mode('Document',pick=True,cancel=True)
        run.pick_placement.assert_called_once()
        run.bake.assert_not_called()
        run.doc.EndUndoRecord.assert_called_once_with(7)
        run.drawing['objects'][0]['geometry'].Dispose.assert_called_once()

    def test_failed_generation_does_not_bake_and_closes_undo(self):
        run = self.run_mode('Document',fail=True)
        run.bake.assert_not_called()
        run.doc.EndUndoRecord.assert_called_once_with(7)
        run.drawing['objects'][0]['geometry'].Dispose.assert_not_called()

    def test_placement_does_not_recompute(self):
        run = self.run_mode('Placement')
        run.reposition_drawing.assert_called_once()
        run.generate.assert_not_called()
        run.drawing['objects'][0]['geometry'].Dispose.assert_not_called()

    def test_pdf_uses_world_origin_without_bake_or_undo(self):
        run = self.run_mode('PDF',pick=True)
        self.assertIs(run.generate.call_args.args[4],run.world)
        run.export_pdf.assert_called_once()
        run.bake.assert_not_called()
        run.pick_placement.assert_not_called()
        run.doc.BeginUndoRecord.assert_not_called()


if __name__=='__main__': unittest.main()
