"""Selection and noninteractive routing only; native geometry is checked in Rhino."""
import importlib.util
import contextlib
import io
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

    def test_move_requires_all_points_and_finite_xyz_before_dispatch(self):
        for points in ({A:[1,2]}, {A:[1,2],B:[3,float('nan')]}, {A:[1,2],B:[3,4,float('nan')]}):
            with self.subTest(points=points), patch.object(ps, 'clipping_planes', return_value=self.planes), \
                 patch.object(ps, 'run_selected') as execute, self.assertRaises(ValueError):
                ps.run(object(), 'Move', [A,B], points=points)
            execute.assert_not_called()

    def test_public_create_and_move_preserve_xyz_and_legacy_xy(self):
        class Plane:
            WorldXY = object()
            def __init__(self, source): self.Origin = NS(X=0, Y=0, Z=0)
        geometry = NS(Plane=Plane, Point3d=lambda x,y,z:NS(X=x,Y=y,Z=z))
        for operation in ('Create', 'Move'):
            for height in (100, -3900):
                with self.subTest(operation=operation, height=height), \
                     patch.object(ps, 'G', geometry), \
                     patch.object(ps, 'clipping_planes', return_value=self.planes), \
                     patch.object(ps, 'run_selected', return_value='batch') as execute:
                    self.assertEqual(ps.run(object(), operation, [A,B],
                                            points={A:[10,20,height], B:[30,40]}), 'batch')
                    targets = execute.call_args.args[4]
                    self.assertEqual(vars(targets[A].Origin), dict(X=10,Y=20,Z=height))
                    self.assertEqual(vars(targets[B].Origin), dict(X=30,Y=40,Z=0))

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

    def test_batch_reports_partial_without_erasing_prior_completed_output(self):
        doc = Mock(CurrentUndoRecordSerialNumber=41)
        app = NS(RhinoApp=NS(Wait=lambda:None, EscapeKeyPressed=MagicMock()))
        def process(doc, cp, options, folder, progress, cancelled, cache, target, result):
            if cp.Id == B: raise ValueError('second clipping failed')
            result['object_ids'] = ['new-output']
            result['report'] = {'section':1}
            return 'completed'
        with patch.object(ps,'R',app), patch.object(ps,'process_clipping',side_effect=process), \
             patch.object(ps,'ModelCache',return_value=NS(Dispose=Mock())), \
             contextlib.redirect_stdout(io.StringIO()):
            outcome = ps.run_selected(doc,self.planes,ps.default_options())
        self.assertEqual((outcome['status'],outcome['completed'],outcome['requested']),('partial',1,2))
        self.assertEqual([i['status'] for i in outcome['results']],['completed','failed'])
        self.assertEqual(outcome['results'][0]['object_ids'],['new-output'])
        self.assertIn('second clipping failed',outcome['results'][1]['error'])
        doc.BeginUndoRecord.assert_not_called()
        doc.EndUndoRecord.assert_not_called()


class InitialOptions(unittest.TestCase):
    def setup_getter(self, results, change=False):
        class Getter:
            def __init__(self):
                self.get_results = list(results)
                self.options_at_first_get = None
                self.options = []
                self.output = NS(CurrentListOptionIndex=1 if change else 0)
                self.toggles = {}
                self.disposed = False
                self.OptionIndex = lambda: 1
                self.Option = lambda: self.output
            def SetCommandPrompt(self, value): self.prompt = value
            def AcceptNothing(self, value): pass
            def ClearCommandOptions(self): self.options = []
            def AddOption(self, name): self.options.append(name)
            def AddOptionList(self, name, choices, index):
                self.options.append(name)
                return 1
            def AddOptionToggle(self, name, value):
                self.options.append(name)
                self.toggles[name] = value
            def AddOptionDouble(self, name, value): self.options.append(name)
            def Get(self):
                if self.options_at_first_get is None:
                    self.options_at_first_get = list(self.options)
                if change and len(self.get_results) == 2:
                    self.toggles['Hatch'].CurrentValue = False
                return self.get_results.pop(0)
            def Dispose(self): self.disposed = True

        getter = Getter()
        sticky = {'PlanSection:style_defaults':[.09,.04,80.,45.]}
        def Toggle(value, *_): return NS(CurrentValue=value)
        def Double(value, *_): return NS(CurrentValue=value)
        rhino = NS(Input=NS(GetResult=NS(Option='option', Nothing='enter'),
            Custom=NS(GetOption=lambda:getter, OptionToggle=Toggle, OptionDouble=Double)))
        return getter, sticky, rhino

    def test_options_are_directly_present_without_change_gate(self):
        getter, sticky, rhino = self.setup_getter(['option','enter'], change=True)
        with patch.object(ps,'R',rhino), patch.object(ps,'System',NS(Double=NS(MaxValue=1e9))), \
             patch.dict(sys.modules,{'scriptcontext':NS(sticky=sticky)}):
            result = ps.get_options('Create')
        self.assertIn('Output',getter.options_at_first_get)
        self.assertIn('Hatch',getter.options_at_first_get)
        self.assertIn('PickPlacement',getter.options_at_first_get)
        self.assertNotIn('Change',getter.options_at_first_get)
        self.assertEqual((result['mode'],result['hatch']),('Files',False))
        self.assertEqual(sticky['PlanSection:options']['mode'],'Files')
        self.assertTrue(getter.disposed)

    def test_escape_discards_option_changes_without_touching_sticky(self):
        getter, sticky, rhino = self.setup_getter(['option','cancel'], change=True)
        previous = dict(sticky)
        with patch.object(ps,'R',rhino), patch.object(ps,'System',NS(Double=NS(MaxValue=1e9))), \
             patch.dict(sys.modules,{'scriptcontext':NS(sticky=sticky)}):
            self.assertIsNone(ps.get_options('Create'))
        self.assertEqual(sticky,previous)
        self.assertTrue(getter.disposed)


if __name__ == '__main__': unittest.main()
