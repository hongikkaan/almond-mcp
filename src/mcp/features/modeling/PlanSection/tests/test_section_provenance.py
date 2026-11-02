"""Planar-section provenance at the actual union-region boundary (mock Rhino)."""
from types import SimpleNamespace as NS
from unittest.mock import patch
import unittest

from test_logic import ps, Attributes


class Box:
    def Inflate(self, tolerance): pass


class Tree:
    def __init__(self): self.items = []
    def Insert(self, box, index): self.items.append(index)
    def Search(self, box, callback):
        # Deliberately return every candidate even when source regions are
        # disjoint. Only *native planar intersection* may prove contribution.
        for index in self.items: callback(None, NS(Id=index))
    def Dispose(self): pass


class Curve:
    def __init__(self, owner, closed=True):
        self.owner, self.IsClosed = owner, closed


class Source:
    def __init__(self, owner, closed=True):
        self.owner, self.IsSolid = owner, closed
        self.Faces = NS(Count=2 if closed else 1)
        self.IsValid = True
    def GetBoundingBox(self, accurate): return Box()


class Region:
    def __init__(self, members):
        self.members, self.IsValid = set(members), True
    def GetBoundingBox(self, accurate): return Box()
    def Dispose(self): pass


class Axis:
    def __init__(self, x, y): self.x, self.y = x, y
    def __mul__(self, other):
        if isinstance(other, Axis): return self.x*other.x+self.y*other.y
        return Axis(self.x*other, self.y*other)
    def __rmul__(self, other): return self*other
    def __add__(self, other): return Axis(self.x+other.x,self.y+other.y)


class SectionProvenance(unittest.TestCase):
    def section(self, entries, merged=False, hatch=False):
        style = NS(HatchIndex=2, BackgroundFillMode='None', SectionFillRule='closed',
                   HatchRotationRadians=0., HatchScale=1., HatchPatternColor=NS(A=0))
        sources = [Source(name, closed) for name, closed in entries]
        records = [dict(geometry=src, source=str(i), attributes=Attributes(name=name),
                        resolved=NS(GetCustomSectionStyle=lambda: style,ObjectColor=NS(A=0)),
                        source_metadata=dict(name=name, user_text={}, dictionary={}))
                   for i, ((name, closed), src) in enumerate(zip(entries, sources))]
        plane = NS(XAxis=Axis(1,0),YAxis=Axis(0,1),Origin=(0,0))
        intersection_calls = []
        class Brep(Source):
            @staticmethod
            def CreatePlanarBreps(curves, tol):
                return [Region([curve.owner]) for curve in curves]
            @staticmethod
            def CreatePlanarIntersection(result, source, plane, tol):
                intersection_calls.append((set(result.members), set(source.members)))
                return [Region(source.members)] if source.members <= result.members else []
        # Closed input models are fake Breps, open surfaces use single-face Breps.
        for source in sources: source.__class__ = Brep
        def planar_union(regions, _plane, _tol):
            return [Region(set().union(*(reg.members for reg in regions)))] if merged else regions
        def drawing_attributes(doc, resolved, sources, role, metadata=None):
            attrs = Attributes()
            attrs.ObjectColor = NS(A=0)
            return attrs
        def hatch_object(boundary, index, angle, scale, tol, region):
            return [NS(Plane=plane, IsValid=True)]
        fake_G = NS(Brep=Brep, Mesh=type('Mesh',(),{}), RTree=Tree,
                    AreaMassProperties=NS(Compute=lambda region: NS(
                        Area=float(len(region.members)), AreaError=0., Dispose=lambda:None)))
        fake_D = NS(ObjectSectionFillRule=NS(ClosedCurves='closed'),
                    ObjectPlotColorSource=NS(PlotColorFromLayer='layer'),
                    ObjectColorSource=NS(ColorFromObject='object'))
        fake_R = NS(RhinoMath=NS(UnsetIntIndex=-1))
        with patch.object(ps,'G',fake_G), patch.object(ps,'D',fake_D), patch.object(ps,'R',fake_R), \
             patch.object(ps,'section_tolerance',return_value=.01), \
             patch.object(ps,'record_bounds',return_value=None), \
             patch.object(ps,'meets_plane',return_value=True), \
             patch.object(ps,'intersect',side_effect=lambda geo,plane,tol:[Curve(geo.owner,geo.IsSolid)]), \
             patch.object(ps,'clean_closed_curve',side_effect=lambda curve,*args:([curve],[])), \
             patch.object(ps,'planar_union',side_effect=planar_union), \
             patch.object(ps,'region_boundaries',side_effect=lambda region,*args:[Curve(','.join(sorted(region.members)))]), \
             patch.object(ps,'split_crossings',side_effect=lambda curve,*args:([curve],False,False)), \
             patch.object(ps,'style_key',return_value='same'), \
             patch.object(ps,'drawing_metadata',return_value=('sources','layer','style')), \
             patch.object(ps,'drawing_attributes',side_effect=drawing_attributes), \
             patch.object(ps,'create_hatches',side_effect=hatch_object), \
             patch.object(ps,'hatch_pattern',return_value=NS(Index=2)):
            result = ps.sections(NS(ModelAbsoluteTolerance=.01,ModelAngleToleranceRadians=.01,
                                    Layers=[NS(FullPath='Model')]),records,plane,hatch)
        return result, intersection_calls

    def test_disjoint_equal_style_regions_keep_individual_source_names(self):
        items, calls = self.section([('Wall A',True),('Wall B',True)])
        self.assertEqual(len(items),2)
        self.assertEqual([set(i['contributors']) for i in items],[{'0'},{'1'}])
        self.assertEqual([ps.consensus_metadata(list(i['contributors'].items()))['name']
                          for i in items],['Wall A','Wall B'])
        self.assertTrue(calls)  # Overlapping candidate boxes alone do not prove ownership.

    def test_union_of_touching_or_overlapping_regions_reports_name_conflict(self):
        items, calls = self.section([('Wall A',True),('Wall B',True)],merged=True)
        self.assertEqual(len(items),1)
        self.assertEqual(set(items[0]['contributors']),{'0','1'})
        agreed = ps.consensus_metadata(list(items[0]['contributors'].items()))
        self.assertEqual(agreed['name'],'')
        self.assertEqual(agreed['conflicts'][0]['field'],'Name')

    def test_open_section_and_solid_hatch_have_separate_contributors(self):
        items, calls = self.section([('Open face',False),('Solid wall',True)],
                                    hatch=True)
        sections = [i for i in items if i['role']=='section']
        hatches = [i for i in items if i['role']=='hatch']
        self.assertEqual(len(sections),2)
        self.assertEqual(len(hatches),1)
        self.assertEqual({i['geometry'].owner:tuple(i['contributors']) for i in sections},
                         {'Open face':('0',),'Solid wall':('1',)})
        self.assertEqual(set(hatches[0]['contributors']),{'1'})


if __name__ == '__main__':
    unittest.main()
