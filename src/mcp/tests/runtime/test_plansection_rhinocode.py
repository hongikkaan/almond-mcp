"""Actual RhinoCode wrapper + PlanSection orchestration, with no live model/API."""
import json
from pathlib import Path
import sys
from unittest.mock import MagicMock

import pytest
import rhinocode as rc
from test_rhinocode import execution, _fake_rhino, inspect


SCRIPT = Path(__file__).resolve().parents[2] / 'features/modeling/PlanSection/PlanSection.py'
IDS = ['11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222']


@pytest.mark.parametrize('plan_cwd', [False, True])
@pytest.mark.parametrize('partial', [False, True])
def test_guid_batch_uses_bound_doc_outer_undo_and_json_receipt(execution, monkeypatch, plan_cwd, partial):
    doc, context, previous_doc = _fake_rhino(execution, monkeypatch)
    rhino = sys.modules['Rhino']
    rhino.Geometry, rhino.DocObjects = MagicMock(), MagicMock()
    rhino.RhinoApp.Wait = lambda: None
    rhino.RhinoApp.EscapeKeyPressed = MagicMock()
    for name in ('clr', 'System.Drawing', 'System.Collections.Generic'):
        monkeypatch.setitem(sys.modules, name, MagicMock())
    # A prompt would fail instead of hanging an unattended execution.
    monkeypatch.setitem(sys.modules, 'rhinoscriptsyntax', None)
    directory = execution.root / 'tmp' / 'PlanSection'
    source = '''import os, runpy, scriptcontext
from types import SimpleNamespace
assert doc is scriptcontext.doc
ps = runpy.run_path(SCRIPT_PATH)
ids = CLIPPING_IDS
scope = ps['run'].__globals__
scope['clipping_planes'] = lambda current: [SimpleNamespace(Id=value, Name='단면') for value in ids]
def geometry_boundary(current, cp, options, folder, progress, cancelled, cache, target, row):
    assert current is doc and doc.CurrentUndoRecordSerialNumber == 9
    assert cache.document == doc.RuntimeSerialNumber
    assert options['mode'] == 'Document' and not options['pick']
    if PARTIAL and cp.Id == ids[1]:
        raise ValueError('second drawing failed')
    row['object_ids'] = ['33333333-3333-3333-3333-333333333333']
    return 'completed'
scope['process_clipping'] = geometry_boundary
result = ps['run'](doc, 'Create', ids)
result['cwd'] = os.getcwd()
'''.replace('SCRIPT_PATH', repr(str(SCRIPT))).replace('CLIPPING_IDS', repr(IDS)).replace('PARTIAL', repr(partial))
    _, wrapper = rc.build_wrapper(execution.journal, source, execution.directory,
        project_root=str(execution.root), artifact_dir='tmp/PlanSection',
        executable=execution.root / 'rhinocode.exe',
        working_directory=str(directory) if plan_cwd else None)
    previous_cwd, previous_stdout, previous_stderr = Path.cwd(), sys.stdout, sys.stderr
    exec(compile(wrapper, 'plansection_wrapper.py', 'exec'), {})
    final = json.loads((execution.directory / 'complete.json').read_text())
    assert final['status'] == 'success', final
    result = json.loads((execution.directory / 'result.json').read_text())
    assert result['status'] == ('partial' if partial else 'completed')
    assert result['completed'] == (1 if partial else 2)
    assert [row['clipping_id'] for row in result['results']] == IDS
    if partial:
        assert result['results'][1]['error'] == 'second drawing failed'
    assert Path(result['cwd']) == (directory if plan_cwd else execution.root)
    assert doc.begins == 1, 'PlanSection must reuse the RhinoCode-owned Undo record'
    assert final['undo']['owned'] == 9 and final['undo']['ended']
    assert inspect(execution)['completed']
    assert context.doc is previous_doc and doc.Views.RedrawEnabled
    assert Path.cwd() == previous_cwd
    assert sys.stdout is previous_stdout and sys.stderr is previous_stderr
