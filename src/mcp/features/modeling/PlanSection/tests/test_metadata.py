"""Offline metadata behavior; RhinoCommon storage needs a separate native check."""
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from test_logic import ps


class Point:
    def __init__(self, x, y, z):
        self.X, self.Y, self.Z = x, y, z
        self.IsValid = True


class Axis:
    def __init__(self, x, y, z):
        self.X, self.Y, self.Z = x, y, z


class Plane:
    def __init__(self, source=None, xaxis=None, yaxis=None):
        source = source or Point(0, 0, 0)
        if isinstance(source, Plane):
            self.Origin = Point(source.OriginX, source.OriginY, source.OriginZ)
            self.XAxis, self.YAxis = source.XAxis, source.YAxis
        else:
            self.Origin = Point(source.X, source.Y, source.Z)
            self.XAxis = xaxis or Axis(1, 0, 0)
            self.YAxis = yaxis or Axis(0, 1, 0)
        self.IsValid = True

    @property
    def OriginX(self): return self.Origin.X

    @property
    def OriginY(self): return self.Origin.Y

    @property
    def OriginZ(self): return self.Origin.Z


Plane.WorldXY = Plane()


class Dictionary:
    def __init__(self, values=None):
        self.values = dict(values or {})
    @property
    def Keys(self): return list(self.values)
    def ContainsKey(self, key): return key in self.values
    def __getitem__(self, key): return self.values[key]
    def Set(self, key, value):
        self.values[key] = value
        return True


class Attributes:
    def __init__(self, name='', user_text=None, dictionary=None):
        self.Name = name
        self.user_text = dict(user_text or {})
        self.UserDictionary = Dictionary(dictionary)
    def GetUserString(self, key): return self.user_text.get(key)
    def SetUserString(self, key, value):
        self.user_text[key] = value
        return True
    def GetUserStrings(self): return NS(AllKeys=list(self.user_text))
    def Duplicate(self):
        return Attributes(self.Name, self.user_text, self.UserDictionary.values)
    def DeleteAllUserStrings(self): self.user_text.clear()


class TypedPlacement(unittest.TestCase):
    def setUp(self):
        self.geometry = NS(Plane=Plane, Point3d=Point, Vector3d=Axis)
        self.patch = patch.object(ps, 'G', self.geometry)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_typed_draft_plane_and_output_point_write_with_json_mirror(self):
        for key, kind in (('draft_plane', Plane), ('ps:placement', Point)):
            with self.subTest(key=key):
                attrs = Attributes()
                plane = Plane(Point(2, 3, -3900))
                ps.write_saved_plane(attrs, key, plane)
                self.assertIsInstance(attrs.UserDictionary[key], kind)
                self.assertEqual(ps.read_saved_plane(attrs, key).OriginZ, -3900)
                self.assertEqual(ps.draft_plane(attrs.GetUserString(key)).OriginZ, -3900)

    def test_legacy_json_read_and_typed_mismatch_fails_explicitly(self):
        attrs = Attributes(user_text={'ps:placement': ps.plane_json(Plane(Point(1, 2, 3)))})
        self.assertEqual(ps.read_saved_plane(attrs, 'ps:placement').OriginZ, 3)
        attrs.UserDictionary.Set('ps:placement', Point(1, 2, 4))
        with self.assertRaisesRegex(ValueError, 'conflict'):
            ps.read_saved_plane(attrs, 'ps:placement')
        attrs.UserDictionary.Set('ps:placement', 'bad-typed-value')
        with self.assertRaisesRegex(ValueError, '(?i)invalid typed'):
            ps.read_saved_plane(attrs, 'ps:placement')

    def test_typed_draft_plane_preserves_axes_and_rejects_conflicting_json(self):
        attrs = Attributes()
        plane = Plane(Point(5, 7, 11))
        ps.write_saved_plane(attrs, 'draft_plane', plane)
        self.assertIsInstance(ps.read_saved_plane(attrs, 'draft_plane'), Plane)
        attrs.SetUserString('draft_plane', ps.plane_json(Plane(Point(5, 7, 12))))
        with self.assertRaisesRegex(ValueError, 'conflict'):
            ps.read_saved_plane(attrs, 'draft_plane')

    def test_move_changes_only_position_and_retains_legacy_name_floor_and_notes(self):
        class MovePoint(Point):
            def __sub__(self, other):
                return (self.X-other.X,self.Y-other.Y,self.Z-other.Z)
        before = Plane(MovePoint(10, 20, 100))
        after = Plane(MovePoint(30, 40, -3900))
        before.Origin = MovePoint(10,20,100)
        after.Origin = MovePoint(30,40,-3900)
        attrs = Attributes('Edited after Create', {'ps:placement':ps.plane_json(before),
                                                   'manual':'keep me'}, {'Floor':'OriginalFloor'})
        geometry = Mock()
        geometry.Duplicate.side_effect = [Mock(),Mock(IsValid=True,Transform=Mock(return_value=True))]
        obj = NS(Id='old-id',Geometry=geometry,Attributes=attrs)
        doc = NS(Objects=NS(Replace=Mock(return_value=True),
                            FindId=Mock(return_value=obj), ModifyAttributes=Mock(return_value=True)))
        cp = NS(Id='clip',Name='clipping',IsReference=True,Attributes=Attributes())
        with patch.object(ps,'drawing_objects',return_value=[obj]), \
             patch.object(ps,'saved_placement',return_value=before), \
             patch.object(ps,'placement_plane',return_value=after), \
             patch.object(ps,'save_drawing_registry'), \
             patch.object(ps,'G',NS(Point3d=MovePoint,Plane=Plane,
                                   Transform=NS(Translation=lambda value:value))):
            self.assertTrue(ps.reposition_drawing(doc,cp,after))
        written = doc.Objects.ModifyAttributes.call_args.args[1]
        self.assertEqual(written.Name,'Edited after Create')
        self.assertEqual(written.UserDictionary['Floor'],'OriginalFloor')
        self.assertEqual(written.GetUserString('manual'),'keep me')
        self.assertIsInstance(written.UserDictionary['ps:placement'],MovePoint)
        self.assertIn('-3900',written.GetUserString('ps:placement'))


class SourceMetadata(unittest.TestCase):
    def test_source_names_and_fields_need_agreement_of_every_contributor(self):
        a = Attributes('Door', {'Phase': 'A', 'ps:generator': 'source'}, {'Type': 'Opening', 'Rating': 2})
        b = Attributes('Door', {'Phase': 'A'}, {'Type': 'Opening', 'Rating': 3})
        result = ps.consensus_metadata([('first', ps.source_metadata(a)), ('second', ps.source_metadata(b))])
        self.assertEqual(result['name'], 'Door')
        self.assertEqual(result['user_text'], {'Phase':'A'})
        self.assertEqual(result['dictionary'], {'Type':'Opening'})
        self.assertEqual([i['field'] for i in result['conflicts']], ['user_dictionary.Rating'])
        self.assertEqual(result['conflicts'][0]['sources'], ['first','second'])
        self.assertNotIn('ps:generator', result['user_text'])

    def test_unnamed_and_name_conflicts_cannot_inherit_arbitrary_first(self):
        for names in (('', 'Door'), ('Door', 'Window'), ('', '')):
            with self.subTest(names=names):
                sources = [(str(i), ps.source_metadata(Attributes(name))) for i, name in enumerate(names)]
                self.assertEqual(ps.consensus_metadata(sources)['name'], '')

    def test_reserved_and_floor_do_not_override_output_floor(self):
        src = Attributes('Wall', {'Floor':'5F'},
                         {'Floor': ['5F','6F'], 'ps:clip': 'forged', 'MaterialClass':'wall'})
        result = ps.consensus_metadata([('source', ps.source_metadata(src))])
        self.assertNotIn('Floor', result['dictionary'])
        self.assertNotIn('Floor', result['user_text'])
        self.assertNotIn('ps:clip', result['dictionary'])
        attrs = Attributes()
        ps.apply_source_metadata(attrs, result, '5F')
        self.assertEqual(attrs.UserDictionary['Floor'], '5F')
        self.assertEqual(attrs.UserDictionary['MaterialClass'], 'wall')
        self.assertEqual(src.UserDictionary['Floor'], ['5F','6F'])

    def test_generate_and_output_boundary_preserve_only_consensus(self):
        first = Attributes('Partition', {'Phase':'A'}, {'Class':'Wall', 'Floor':['5F','6F']})
        second = Attributes('Partition', {'Phase':'A'}, {'Class':'Wall', 'Floor':['7F']})
        sources = {'left':ps.source_metadata(first), 'right':ps.source_metadata(second)}
        item = dict(geometry=NS(Dispose=Mock()), attributes=Attributes(), role='section',
                    contributors=sources)
        original = NS(Dispose=Mock())
        records = [{'geometry':original, 'attributes':first, 'resolved':Attributes()}]
        clip = NS(Id='clip', Name='6F')
        with patch.object(ps,'read_clip',return_value=dict(plane='cut',depth=None,target='target')), \
             patch.object(ps,'model_objects',return_value=records), \
             patch.object(ps,'sections',return_value=[item]), \
             patch.object(ps,'section_tolerance',return_value=.01), \
             patch.object(ps,'deduplicate',side_effect=lambda items,*args:items), \
             patch.object(ps,'cleanup_elevations',side_effect=lambda doc,items,*args:(items,{})):
            generated = ps.generate(NS(ModelAbsoluteTolerance=.01),clip,elevation=False,place=False)
        attrs = ps.output_attributes(generated['objects'][0]['attributes'])
        self.assertEqual(attrs.Name,'Partition')
        self.assertEqual(attrs.UserDictionary['Floor'],'6F')
        self.assertEqual(attrs.UserDictionary['Class'],'Wall')
        self.assertEqual(attrs.GetUserString('Phase'),'A')
        self.assertIsNone(attrs.GetUserString('ps:inherited_keys'))
        self.assertIsNone(attrs.GetUserString('ps:clip'))
        self.assertEqual(generated['report']['metadata_conflict_count'],0)
        self.assertEqual(first.UserDictionary['Floor'],['5F','6F'])
        self.assertEqual(second.UserDictionary['Floor'],['7F'])
        self.assertEqual(original.Dispose.call_count,1)

    def test_conflict_report_preserves_contributor_ids_after_generate(self):
        left = ps.source_metadata(Attributes('Door', dictionary={'Phase':'A'}))
        right = ps.source_metadata(Attributes('Window', dictionary={'Phase':'B'}))
        item = dict(geometry=NS(Dispose=Mock()),attributes=Attributes(),role='elevation',
                    contributors={'block/left':left, 'block/right':right})
        records = [dict(geometry=NS(Dispose=Mock()),attributes=Attributes(),resolved=Attributes())]
        with patch.object(ps,'read_clip',return_value=dict(plane='cut',depth=None,target='target')), \
             patch.object(ps,'model_objects',return_value=records), \
             patch.object(ps,'sections',return_value=[item]), \
             patch.object(ps,'section_tolerance',return_value=.01), \
             patch.object(ps,'deduplicate',side_effect=lambda items,*args:items), \
             patch.object(ps,'cleanup_elevations',side_effect=lambda doc,items,*args:(items,{})):
            generated = ps.generate(NS(ModelAbsoluteTolerance=.01),NS(Id='clip',Name='3F'),
                                    elevation=False,place=False)
        self.assertEqual(generated['objects'][0]['attributes'].Name,'')
        conflicts = generated['report']['metadata_conflicts']
        self.assertEqual([c['field'] for c in conflicts],['Name','user_dictionary.Phase'])
        self.assertTrue(all(c['sources']==['block/left','block/right'] for c in conflicts))


if __name__ == '__main__':
    unittest.main()
