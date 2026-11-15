"""Actual input summaries and metadata replacement guards; no Rhino process."""
import json
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from test_logic import ps, Attributes, clipping
from test_metadata import Plane, Point


class GenerationContract(unittest.TestCase):
    def test_conditions_describe_actual_distinct_sources_and_layers(self):
        records = [dict(source='block/member', attributes=Attributes(layer=1), hidden=True, locked=False, reference=True),
                   dict(source='block/member', attributes=Attributes(layer=1), hidden=True, locked=False, reference=True),
                   dict(source='local', attributes=Attributes(layer=0), hidden=False, locked=True, reference=False)]
        doc = NS(Layers=[NS(FullPath='Model::Walls'), NS(FullPath='Attach::Core')])
        clip = dict(plane=Plane(), target=Plane(Point(10, 20, 100)), depth=200, enabled=True)
        with patch.object(ps, 'placement_plane', side_effect=lambda cut, origin: Plane(origin)):
            actual = ps.generation_conditions(doc, clip, records, True)
        self.assertEqual(actual['source_object_count'], 2)
        self.assertEqual(actual['source_layer_names'], ['Attach::Core', 'Model::Walls'])
        self.assertTrue(actual['include_references'] and actual['reference_objects_included'])
        self.assertTrue(actual['hidden_objects_included'] and actual['locked_objects_included'])
        self.assertEqual(actual['drawing_plane']['origin'], [10, 20, 100])
        self.assertEqual(actual['clipping_plane']['origin'], [0, 0, 0])
        self.assertNotIn('object_ids', actual)

    def test_layer_visibility_is_not_reported_as_object_hidden_or_locked(self):
        doc = NS(Layers=[NS(FullPath='Model', IsVisible=False, IsLocked=True)])
        clip = dict(plane=Plane(), target=Plane(), depth=None, enabled=False)
        records = [dict(source='object', attributes=Attributes(), hidden=False, locked=False, reference=False)]
        with patch.object(ps, 'placement_plane', side_effect=lambda cut, origin: Plane(origin)):
            actual = ps.generation_conditions(doc, clip, records, False)
        self.assertFalse(actual['hidden_objects_included'] or actual['locked_objects_included'])
        self.assertFalse(actual['reference_objects_included'] or actual['include_references'])

    def test_invalid_source_preserves_prior_output_and_disposes_owned_input(self):
        source = NS(Dispose=Mock())
        records = [dict(geometry=source)]
        def collect(doc, clip, issues, *args):
            issues['invalid'] = 1
            return records
        with patch.object(ps, 'read_clip', return_value={}), \
             patch.object(ps, 'model_objects', side_effect=collect), \
             patch.object(ps, 'sections') as sections, \
             self.assertRaisesRegex(ValueError, 'previous valid output retained'):
            ps.generate(NS(), clipping())
        sections.assert_not_called()
        source.Dispose.assert_called_once()

    def test_new_ownership_markers_survive_output_boundary(self):
        attrs = Attributes({'ps:generator': ps.OWNER, 'ps:clip': 'clipping', 'ps:source_layer': 'Model', 'ps:placement': 'saved'})
        result = ps.output_attributes(attrs)
        self.assertEqual(result.GetUserString('ps:generator'), ps.OWNER)
        self.assertEqual(result.GetUserString('ps:clip'), 'clipping')
        self.assertEqual(attrs.GetUserString('ps:clip'), 'clipping')

    def test_unchanged_generated_metadata_allows_update_but_user_edits_are_protected(self):
        attrs = Attributes({'Phase': 'A', 'ps:placement': 'old'}, name='Wall', dictionary={'Floor': '3F'})
        attrs.SetUserString('ps:metadata_snapshot', json.dumps(ps.output_metadata_snapshot(attrs)))
        obj = NS(Attributes=attrs)
        attrs.SetUserString('ps:placement', 'new')
        ps.protect_existing_output([obj])
        for field in ('name', 'user_text', 'dictionary'):
            edited = attrs.Duplicate()
            if field == 'name': edited.Name = 'User label'
            elif field == 'user_text': edited.SetUserString('OwnerNote', 'Keep me')
            else: edited.UserDictionary.Set('Floor', 'USER')
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'user-edited'):
                ps.protect_existing_output([NS(Attributes=edited)])
        self.assertEqual(attrs.Name, 'Wall')

    def test_legacy_and_broken_baseline_are_preserved_without_guessing_mapping(self):
        ps.protect_existing_output([NS(Attributes=Attributes())])
        for attrs in (Attributes({'Note':'manual'}), Attributes(name='manual'),
                      Attributes({'ps:metadata_snapshot':'broken'})):
            with self.assertRaises(ValueError): ps.protect_existing_output([NS(Attributes=attrs)])

    def test_legacy_only_generated_floor_exact_value_and_type_is_lossless(self):
        exact = Attributes(dictionary={'Floor': 'Plan'})
        ps.protect_existing_output([NS(Attributes=exact)], generated_floor='Plan')
        for attrs in (Attributes(dictionary={'Floor': 'Other'}), Attributes(dictionary={'Floor': ['Plan']}),
                      Attributes(dictionary={'Floor':'Plan', 'Note':'keep'}), Attributes({'Note':'keep'}, dictionary={'Floor':'Plan'}),
                      Attributes(name='Manual', dictionary={'Floor':'Plan'})):
            with self.assertRaises(ValueError):
                ps.protect_existing_output([NS(Attributes=attrs)], generated_floor='Plan')
        self.assertEqual(exact.UserDictionary['Floor'], 'Plan')

    def test_legacy_floor_survives_actual_move_then_update_chain(self):
        import test_output_space as output_space
        attrs = output_space.Attributes()
        attrs.UserDictionary.Set('Floor', 'Plan')
        before, after = Mock(), Mock(IsValid=True)
        after.Transform.return_value = True
        geometry = Mock()
        geometry.Duplicate.side_effect = [before, after]
        obj = NS(Id='drawing', Geometry=geometry, Attributes=attrs)
        doc = NS(Objects=NS(Replace=Mock(return_value=True), FindId=Mock(return_value=obj),
                            ModifyAttributes=Mock(return_value=True)))
        cp = NS(IsReference=True, Name='Plan', Attributes=output_space.Attributes())
        target = NS(Origin=10)
        with patch.object(ps, 'G', NS(Plane=NS(WorldXY=object()), Transform=NS(Translation=lambda value:value))), \
             patch.object(ps, 'drawing_objects', return_value=[obj]), \
             patch.object(ps, 'saved_placement', return_value=NS(Origin=0)), \
             patch.object(ps, 'placement_plane', return_value=target), \
             patch.object(ps, 'write_saved_plane', side_effect=lambda attrs,key,plane:attrs.SetUserString(key, 'moved')), \
             patch.object(ps, 'save_drawing_registry'):
            self.assertTrue(ps.reposition_drawing(doc, cp, target))
        moved_attrs = doc.Objects.ModifyAttributes.call_args.args[1]
        self.assertEqual(moved_attrs.UserDictionary['Floor'], 'Plan')
        updated = output_space.ModelSpaceOutput().scenario(legacy_attributes=moved_attrs)
        self.assertIsNone(updated.error)
        self.assertEqual(updated.stored['new'].Attributes.UserDictionary['Floor'], 'Plan')
        self.assertTrue(updated.stored['new'].Attributes.GetUserString('ps:metadata_snapshot'))


if __name__ == '__main__': unittest.main()
