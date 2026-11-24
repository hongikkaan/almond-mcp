"""Inject failures at production drawing mutation boundaries; no Rhino runtime."""
from copy import deepcopy
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import pytest
from test_logic import ps, Attributes, clipping


def test_move_deadline_during_preparation_disposes_both_copies_before_first_write():
    before, after = Mock(), Mock(IsValid=True)
    token = NS(expired=False)
    def prepare(_):
        token.expired = True
        return True
    after.Transform.side_effect = prepare
    obj = NS(Id='drawing', Geometry=Mock(), Attributes=Attributes())
    obj.Geometry.Duplicate.side_effect = [before, after]
    doc, result = Mock(), {}
    target = NS(Origin=1)
    with patch.object(ps, 'drawing_objects', return_value=[obj]), patch.object(ps, 'saved_placement', return_value=target), \
         patch.object(ps, 'placement_plane', return_value=target), patch.object(ps,'save_drawing_registry') as registry:
        assert not ps.reposition_drawing(doc,clipping(),target,lambda:token.expired,result)
    before.Dispose.assert_called_once()
    after.Dispose.assert_called_once()
    doc.Objects.Replace.assert_not_called()
    doc.Objects.ModifyAttributes.assert_not_called()
    registry.assert_not_called()
    assert result == {}


@pytest.mark.parametrize('failed_at', [2, 3])
def test_move_recovery_attempts_every_object_attribute_after_replace_throws(failed_at):
    class Point(NS):
        def __sub__(self, other): return (1, 2, 3)
    existing = [NS(Id=str(i), Geometry=Mock(), Attributes=Attributes({'manual': 'keep'})) for i in range(3)]
    for obj in existing:
        obj.Geometry.Duplicate.side_effect = [Mock(), Mock(IsValid=True, Transform=Mock(return_value=True))]
    events = []
    def replace(guid, geo, quiet):
        events.append(('replace', guid))
        if len([e for e in events if e[0] == 'replace']) in (failed_at, failed_at + 1):
            raise ValueError('replace failure')
        return True
    def attributes(guid, attrs, quiet):
        events.append(('attributes', guid))
        return True
    cp = clipping()
    doc = NS(Objects=NS(Replace=replace, ModifyAttributes=attributes,
                       FindId=lambda guid: next(o for o in existing if o.Id == guid)))
    target = NS(Origin=Point())
    with patch.object(ps, 'drawing_objects', return_value=existing), \
         patch.object(ps, 'saved_placement', return_value=target), \
         patch.object(ps, 'placement_plane', return_value=target), \
         patch.object(ps, 'write_saved_plane'), \
         patch.object(ps, 'G', NS(Plane=NS(WorldXY=None), Transform=NS(Translation=lambda _: None))):
        with pytest.raises(ValueError) as caught:
            ps.reposition_drawing(doc, cp, target)
    # A failed geometry restore must not prevent its attributes or other objects/clip restore.
    assert ('attributes', '0') in events[4:]
    assert ('attributes', '1') in events[4:]
    assert ('attributes', 'clip') in events[4:]
    recovery = caught.value.recovery
    assert recovery['mutation_state'] == 'partial'
    assert recovery['requires_reconciliation'] is True
    assert any(a['status'] == 'failed' and a['target'] == str(failed_at-1) for a in recovery['attempts'])


class Layers:
    def __init__(self):
        self.items = [NS(FullPath='Drawing', IsReference=False, IsLocked=False, IsVisible=True,
                         Color='original', PlotColor='original', PlotWeight=1, EnsurePrivateCopy=lambda: None)]
        self.events = []
    def FindByFullPath(self, name, _):
        return next((i for i, v in enumerate(self.items) if v is not None and v.FullPath == name), -1)
    def __getitem__(self, index): return deepcopy(self.items[index])
    def AddPath(self, path):
        self.items.append(NS(FullPath=path, IsReference=False, IsLocked=False, IsVisible=True))
        return len(self.items)-1
    def Modify(self, layer, index, quiet):
        self.events.append(('restore', index)); self.items[index] = layer
        return True
    def Delete(self, index, quiet):
        self.events.append(('delete', index)); self.items[index] = None
        return True


def test_layer_recovery_restores_existing_and_removes_only_owned_created_paths():
    layers = Layers()
    doc = NS(Layers=layers)
    journal = ps.DrawingRecovery()
    ps.local_output_layer(doc, 'Drawing::Section', journal)
    layers.items[0].Color = 'changed'
    journal.restore_layers(doc)
    assert layers[0].Color == 'original'
    assert layers.FindByFullPath('Drawing::Section', -1) == -1
    assert layers.events == [('delete', 1), ('restore', 0)]


def test_registry_mutation_then_exception_restores_owned_layer_snapshot():
    from test_output_space import LayerTable
    layers = LayerTable()
    index = layers.AddPath(ps.DRAWING_ROOT)
    doc = NS(Layers=layers)
    cp = NS(Id='clip')
    original_modify = layers.Modify
    calls = []
    def modify(layer, index, quiet):
        calls.append(index)
        original_modify(layer, index, quiet)
        if len(calls) == 1:
            raise ValueError('registry write failed after mutation')
        return True
    layers.Modify = modify
    journal = ps.DrawingRecovery()
    with pytest.raises(ValueError):
        ps.save_drawing_registry(doc, cp, '["new"]', journal)
    assert layers[index].GetUserString('ps:clip:clip') == '["new"]'
    journal.restore_layers(doc)
    assert layers[index].GetUserString('ps:clip:clip') == 'old-registry'
    assert journal.attempts == [dict(action='layer', target=layer, status='restored')
                                for layer in (ps.DRAWING_ROOT, 'D')]


def test_layer_restore_failure_does_not_skip_remaining_layers():
    layers = Layers()
    doc = NS(Layers=layers)
    journal = ps.DrawingRecovery()
    ps.local_output_layer(doc, 'Drawing::Section', journal)
    layers.Delete = Mock(side_effect=ValueError('locked new layer'))
    layers.items[0].Color = 'changed'
    journal.restore_layers(doc)
    assert layers[0].Color == 'original'
    assert journal.attempts[0]['status'] == 'failed'
    assert journal.attempts[1]['status'] == 'restored'


def test_batch_retains_recovery_details_and_existing_undo_owner():
    journal = ps.DrawingRecovery()
    journal.attempt('geometry', 'x', lambda: False)
    failure = journal.failure(ValueError('write failed'))
    doc = Mock(CurrentUndoRecordSerialNumber=9)
    rhino = NS(RhinoApp=NS(Wait=lambda: None, EscapeKeyPressed=Mock()))
    rhino.RhinoApp.EscapeKeyPressed = type('Event', (), {
        '__iadd__': lambda self, _: self, '__isub__': lambda self, _: self})()
    with patch.object(ps, 'R', rhino), patch.object(ps, 'process_clipping', side_effect=failure):
        result = ps.run_selected(doc, [clipping()], {'mode':'Placement'})
    assert result['results'][0]['recovery'] == failure.recovery
    assert result['requires_reconciliation'] is True
    from jsonschema import validate
    from almond_mcp.output_contracts import CONTRACTS
    validate(result, CONTRACTS['plan_section']['properties']['result'])
    doc.BeginUndoRecord.assert_not_called()
    doc.EndUndoRecord.assert_not_called()
