"""Preflight mandatory response budgets before output mutation, using no Rhino."""
import contextlib
import io
import json
from types import SimpleNamespace as NS
import unittest
from unittest.mock import MagicMock, Mock, patch

from test_logic import ps


def budget_outcome(count=1, layer='Model', budget=32000, source_error=False, mode='Create'):
    planes = [NS(Id='00000000-0000-0000-0000-'+str(i+1).zfill(12), Name='한글도면'+str(i)) for i in range(count)]
    doc = Mock(CurrentUndoRecordSerialNumber=41, RuntimeSerialNumber=41)
    cache = ps.ModelCache(doc)
    geometries = []
    conditions = dict(source_layer_names=[layer], source_object_count=1, include_references=False)
    options = ps.default_options(mode)
    options['_response_budget'] = budget
    def collect(doc, clip, issues, model_cache, references):
        geometry = NS(Dispose=Mock())
        geometries.append(geometry)
        model_cache.entries[clip['identity']] = dict(geometry=geometry)
        if source_error: raise ValueError('preflight source read failed')
        return []
    def execute(*args):
        assert args[6] is cache
        args[-1]['generation_conditions'] = conditions
        args[-1]['output_object_count'] = 1
        return 'completed'
    app = NS(RhinoApp=NS(Wait=lambda:None, EscapeKeyPressed=MagicMock()))
    with patch.object(ps, 'ModelCache', return_value=cache), \
         patch.object(ps, 'read_clip', side_effect=lambda doc, cp, target:dict(identity=cp.Id)), \
         patch.object(ps, 'model_objects', side_effect=collect), \
         patch.object(ps, 'generation_conditions', return_value=conditions), \
         patch.object(ps, 'drawing_objects', return_value=[object()]), \
         patch.object(ps, 'saved_placement', return_value='placement'), \
         patch.object(ps, 'plane_json', return_value='{}'), \
         patch.object(ps, 'process_clipping', side_effect=execute) as process, \
         patch.object(ps, 'R', app), contextlib.redirect_stdout(io.StringIO()):
        outcome = ps.run_selected(doc, planes, options)
    return outcome, process, geometries, cache


class ResponseBudget(unittest.TestCase):
    def test_large_korean_layers_and_many_clippings_reject_before_any_mutation(self):
        for count, layer in ((1, '긴한국어레이어'*1200), (100, '한글레이어'*20)):
            with self.subTest(count=count):
                result, process, geometries, cache = budget_outcome(count, layer)
                self.assertEqual(result['mutation_state'], 'not_started')
                self.assertEqual(result['status'], 'error')
                self.assertEqual(result['error_code'], 'plan_section_response_budget')
                process.assert_not_called()
                self.assertTrue(cache.closed)
                for geometry in geometries: geometry.Dispose.assert_called_once()

    def test_source_preflight_error_is_not_started_and_disposes_prepared_geometry(self):
        result, process, geometries, cache = budget_outcome(source_error=True)
        self.assertEqual(result['error_code'], 'plan_section_preflight_failed')
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['mutation_state'], 'not_started')
        process.assert_not_called()
        self.assertTrue(cache.closed)
        for geometry in geometries: geometry.Dispose.assert_called_once()

    def test_accepted_preflight_reuses_cache_and_disposes_every_record(self):
        result, process, geometries, cache = budget_outcome(4)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(process.call_count, 4)
        self.assertTrue(cache.closed)
        self.assertEqual(len(geometries), 4)
        for geometry in geometries: geometry.Dispose.assert_called_once()

    def test_move_is_budget_checked_before_any_reposition(self):
        result, process, _, _ = budget_outcome(budget=1, mode='Move')
        self.assertEqual(result['mutation_state'], 'not_started')
        process.assert_not_called()

    def test_changed_actual_conditions_are_rechecked_before_bake(self):
        cp = NS(Id='clipping', Name='Plan', ClippingPlaneGeometry=NS(Plane='cut'))
        options = ps.default_options()
        options['_response_budget'] = 32000
        options['_response_rows'] = [ps.response_row(cp, dict(source_layer_names=['before']))]
        drawing = dict(objects=[], report={}, generation_conditions=dict(source_layer_names=['after']))
        with patch.object(ps, 'generate', return_value=drawing), patch.object(ps, 'bake') as bake, \
             self.assertRaisesRegex(ps.ResponseBudgetExceeded, 'changed after preflight'):
            ps.process_clipping(object(), cp, options, None, None, lambda:False)
        bake.assert_not_called()

    def test_ascii_escaped_budget_counts_real_korean_json_bytes(self):
        cp = NS(Id='clip', Name='도면')
        row = ps.response_row(cp, dict(source_layer_names=['레이어'*50]))
        plain = len(json.dumps(row, ensure_ascii=False).encode('utf-8'))
        escaped = len(json.dumps(row, ensure_ascii=True).encode('utf-8'))
        self.assertGreater(escaped, plain)
        with self.assertRaises(ps.ResponseBudgetExceeded):
            ps.response_budget_check(dict(_response_rows=[row], _response_budget=plain))

    def test_mixed_update_skips_missing_output_and_updates_valid_selection(self):
        missing_id = '00000000-0000-0000-0000-000000000001'
        valid_id = '00000000-0000-0000-0000-000000000002'
        planes = [NS(Id=missing_id, Name='Missing', ClippingPlaneGeometry=NS(Plane='cut')),
                  NS(Id=valid_id, Name='Valid', ClippingPlaneGeometry=NS(Plane='cut'))]
        doc = Mock(CurrentUndoRecordSerialNumber=41, RuntimeSerialNumber=41)
        existing = {valid_id: ['old']}
        conditions = dict(source_layer_names=['Model::Valid'], source_object_count=1)
        drawing = dict(objects=[dict(geometry=NS(Dispose=Mock()))], report={}, generation_conditions=conditions)
        def bake(doc, cp, result, target):
            self.assertEqual(cp.Id, valid_id)
            existing[cp.Id] = ['new']
            return ['new']
        app = NS(RhinoApp=NS(Wait=lambda:None, EscapeKeyPressed=MagicMock()))
        with patch.object(ps, 'R', app), \
             patch.object(ps, 'clipping_planes', return_value=planes), \
             patch.object(ps, 'drawing_objects', side_effect=lambda doc,cp:existing.get(cp.Id, [])), \
             patch.object(ps, 'saved_placement', return_value='saved'), \
             patch.object(ps, 'read_clip', return_value={}) as read, \
             patch.object(ps, 'model_objects', return_value=[]), \
             patch.object(ps, 'generation_conditions', return_value=conditions), \
             patch.object(ps, 'response_budget_check', wraps=ps.response_budget_check) as check, \
             patch.object(ps, 'generate', return_value=drawing) as generate, \
             patch.object(ps, 'bake', side_effect=bake) as apply, \
             contextlib.redirect_stdout(io.StringIO()):
            result = ps.run(doc, 'Update', [missing_id, valid_id], response_budget=32000)
        self.assertEqual((result['status'], result['completed'], result['requested']), ('partial', 1, 2))
        skipped, completed = result['results']
        self.assertEqual((skipped['clipping_id'], skipped['status'], skipped['output_object_count']), (missing_id, 'skipped', 0))
        self.assertIsNone(skipped['generation_conditions'])
        self.assertEqual(skipped['message'], 'No existing local drawing; use Create first.')
        self.assertEqual((completed['clipping_id'], completed['status'], completed['output_object_count']), (valid_id, 'completed', 1))
        self.assertEqual(completed['generation_conditions'], conditions)
        self.assertNotIn(missing_id, existing)
        self.assertEqual(existing[valid_id], ['new'])
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(apply.call_count, 1)
        self.assertEqual(read.call_count, 1)  # Missing output does not trigger a source query.
        placeholder = check.call_args_list[0].args[0]['_response_rows'][0]
        self.assertEqual((placeholder['status'], placeholder['output_object_count']), ('skipped', 0))
        self.assertEqual(placeholder['message'], skipped['message'])
        self.assertEqual(result['mutation_state'], 'partial')
        self.assertFalse(result['requires_reconciliation'])


if __name__ == '__main__': unittest.main()
