"""Inject actual algorithm rollback failures without Rhino or a real document."""
import contextlib
import io
from types import SimpleNamespace as NS
import unittest
from unittest.mock import MagicMock, Mock, patch

from test_logic import ps, Attributes, clipping
import test_output_space as output_space

ID = '00000000-0000-0000-0000-000000000001'


def failed_move():
    obj = NS(Id='drawing', Geometry=Mock(), Attributes=Attributes())
    before, after = Mock(), Mock(IsValid=True)
    after.Transform.return_value = True
    obj.Geometry.Duplicate.side_effect = [before, after]
    doc = NS(Objects=NS(Replace=Mock(side_effect=[True, False]),
             ModifyAttributes=Mock(side_effect=[False, RuntimeError('attribute restore failed')]),
             FindId=Mock(return_value=obj)))
    target = NS(Origin=10)
    with patch.object(ps, 'drawing_objects', return_value=[obj]), \
         patch.object(ps, 'saved_placement', return_value=NS(Origin=0)), \
         patch.object(ps, 'placement_plane', return_value=target), \
         patch.object(ps, 'write_saved_plane'), \
         patch.object(ps, 'G', NS(Plane=NS(WorldXY=object()), Transform=NS(Translation=lambda value:value))):
        ps.reposition_drawing(doc, clipping(reference=True), target)


def rollback_outcome(case):
    doc = Mock(CurrentUndoRecordSerialNumber=41)
    app = NS(RhinoApp=NS(Wait=lambda:None, EscapeKeyPressed=MagicMock()))
    cp, later = NS(Id=ID, Name='Plan'), NS(Id='00000000-0000-0000-0000-000000000002', Name='Later')
    def process(*args):
        if case == 'move': failed_move()
        run = output_space.ModelSpaceOutput().scenario(failure=case)
        if run.error is not None: raise run.error
        raise AssertionError('Failure injection did not fail')
    with patch.object(ps, 'R', app), patch.object(ps, 'ModelCache', return_value=NS(Dispose=Mock())), \
         patch.object(ps, 'process_clipping', side_effect=process) as execute, \
         contextlib.redirect_stdout(io.StringIO()):
        result = ps.run_selected(doc, [cp, later], ps.default_options())
    assert execute.call_count == 1, 'An uncertain document must stop the later clipping'
    # Native boundary fixture submits one clipping; retain the actual failed item.
    result['requested'] = 1
    return result


class RollbackContract(unittest.TestCase):
    def test_actual_rollback_failures_are_structured_unknown_and_stop_batch(self):
        for case in ('undelete', 'cleanup', 'registry-restore', 'move'):
            with self.subTest(case=case):
                result = rollback_outcome(case)
                self.assertEqual(result['mutation_state'], 'unknown')
                self.assertTrue(result['requires_reconciliation'])
                item = result['results'][0]
                self.assertEqual(item['error_code'], 'plan_section_rollback_incomplete')
                self.assertTrue(item['rollback_errors'])
                self.assertEqual(item['mutation_state'], 'unknown')


if __name__ == '__main__': unittest.main()
