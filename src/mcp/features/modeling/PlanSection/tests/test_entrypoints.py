"""Selection and noninteractive routing only; native geometry is checked in Rhino."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import MagicMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
with patch.dict(sys.modules, {name: MagicMock() for name in
        ['clr', 'Rhino', 'System', 'System.Drawing', 'System.Collections.Generic']}):
    spec = importlib.util.spec_from_file_location('plansection_entries', ROOT / 'PlanSection.py')
    ps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ps)

A = '11111111-1111-1111-1111-111111111111'
B = '22222222-2222-2222-2222-222222222222'


class EntryPoints(unittest.TestCase):
    def setUp(self):
        self.planes = [NS(Id=A, Name='same'), NS(Id=B, Name='same')]
        for cp in self.planes:
            cp.Document = NS(Layers=[NS(FullPath='existing::clip')])
            cp.Attributes = NS(LayerIndex=0)

    def test_guids_keep_requested_order_and_deduplicate(self):
        self.assertEqual(ps.resolve_clippings(self.planes, B + ', {' + A + '} ' + B),
                         [self.planes[1], self.planes[0]])

    def test_invalid_or_unavailable_guid_rejects_whole_request(self):
        for ids in ([], [A, 'bad'], [A, '33333333-3333-3333-3333-333333333333']):
            with self.subTest(ids=ids), patch.object(ps, 'clipping_planes', return_value=self.planes), \
                 patch.object(ps, 'run_selected') as execute, self.assertRaises(ValueError):
                ps.run(object(), 'Create', ids)
            execute.assert_not_called()

    def test_project_list_opens_dialog(self):
        rs = NS(GetString=Mock(return_value='List'))
        with patch.dict(sys.modules, {'rhinoscriptsyntax':rs}), \
             patch.object(ps, 'select_clipping_list', side_effect=lambda labels: labels) as dialog:
            self.assertEqual(ps.select_clippings(self.planes), self.planes)
        dialog.assert_called_once()

    def test_project_single_number_all_and_reject_comma(self):
        rs = NS(GetString=Mock(side_effect=['1,2', '2']))
        with patch.dict(sys.modules, {'rhinoscriptsyntax':rs}), \
             patch.object(ps, 'select_clipping_list') as dialog:
            self.assertEqual(ps.select_clippings(self.planes), [self.planes[1]])
            self.assertEqual(rs.GetString.call_count, 2)
            rs.GetString = Mock(return_value='All')
            self.assertEqual(ps.select_clippings(self.planes), self.planes)
            rs.GetString = Mock(return_value=None)
            self.assertEqual(ps.select_clippings(self.planes), [])
        dialog.assert_not_called()

    def test_current_document_guid_selection_does_not_open_list(self):
        rs = NS(GetString=Mock(return_value=A + ',' + B))
        with patch.dict(sys.modules, {'rhinoscriptsyntax':rs}), \
             patch.object(ps, 'select_clipping_list') as dialog:
            self.assertEqual(ps.select_clippings(self.planes, 'CurrentDocument'), self.planes)
        dialog.assert_not_called()

    def test_script_offers_project_current_document_choice_before_operation(self):
        for caller in ('Project', 'CurrentDocument'):
            rs = NS(GetString=Mock(side_effect=[caller, 'Create']))
            with self.subTest(caller=caller), patch.dict(sys.modules, {'rhinoscriptsyntax':rs}), \
                 patch.object(ps, 'clipping_planes', return_value=self.planes), \
                 patch.object(ps, 'select_clippings', return_value=self.planes) as select, \
                 patch.object(ps, 'get_options', return_value=ps.default_options()) as options, \
                 patch.object(ps, 'run_selected', return_value='complete'):
                self.assertEqual(ps.main(object()), 'complete')
            self.assertEqual(rs.GetString.call_args_list[0].args[2], ['Project', 'CurrentDocument'])
            select.assert_called_once_with(self.planes, caller)
            options.assert_called_once_with('Create')

    def test_four_operations_route_independently_without_ui(self):
        rs = Mock(side_effect=AssertionError('Unexpected UI'))
        for operation, mode in [('Create','Document'),('Update','Update'),('Move','Placement'),('PDF','PDF')]:
            with self.subTest(operation=operation), patch.dict(sys.modules, {'rhinoscriptsyntax':rs}), \
                 patch.object(ps, 'clipping_planes', return_value=self.planes), \
                 patch.object(ps, 'placement_plane', return_value='target'), \
                 patch.object(ps, 'run_selected', return_value='batch') as execute:
                points = {A:[10,20], B:[30,40,0]} if operation=='Move' else None
                self.assertEqual(ps.run(object(), operation, [A,B], points=points, folder=str(ROOT)), 'batch')
                self.assertEqual(execute.call_args.args[2]['mode'], mode)
                self.assertFalse(execute.call_args.args[2]['pick'])
                if points: self.assertEqual(execute.call_args.args[4], {A:'target', B:'target'})

    def test_move_requires_all_points_and_finite_xy_before_dispatch(self):
        for points in ({A:[1,2]}, {A:[1,2],B:[3,float('nan')]}, {A:[1,2],B:[3,4,5]}):
            with self.subTest(points=points), patch.object(ps, 'clipping_planes', return_value=self.planes), \
                 patch.object(ps, 'run_selected') as execute, self.assertRaises(ValueError):
                ps.run(object(), 'Move', [A,B], points=points)
            execute.assert_not_called()

    def test_update_rejects_points_and_pdf_requires_explicit_folder(self):
        with patch.object(ps, 'clipping_planes', return_value=self.planes), \
             patch.object(ps, 'run_selected') as execute:
            with self.assertRaises(ValueError): ps.run(object(), 'Update', [A], points={A:[1,2]})
            with self.assertRaises(ValueError): ps.run(object(), 'PDF', [A])
        execute.assert_not_called()

    def test_explicit_create_target_reaches_generate_and_bake_without_pick(self):
        cp = self.planes[0]
        cp.ClippingPlaneGeometry = NS(Plane='cut')
        drawing = dict(objects=[], report={})
        with patch.object(ps, 'generate', return_value=drawing) as generate, \
             patch.object(ps, 'bake', return_value=[]) as bake, patch.object(ps, 'pick_placement') as pick:
            ps.process_clipping(object(), cp, ps.default_options(), None, None, lambda:False, target='point')
        self.assertEqual(generate.call_args.args[4], 'point')
        self.assertEqual(bake.call_args.args[3], 'point')
        pick.assert_not_called()

    def test_move_does_not_generate_geometry(self):
        with patch.object(ps, 'reposition_drawing', return_value=True) as move, patch.object(ps, 'generate') as generate:
            self.assertEqual(ps.process_clipping(object(), self.planes[0], ps.default_options('Move'),
                                                None, None, lambda:False, target='point'), 'completed')
        self.assertEqual(move.call_args.args[2], 'point')
        generate.assert_not_called()


if __name__ == '__main__': unittest.main()
