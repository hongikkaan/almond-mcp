"""Recorded paths survive transport; reopening a file is a separate operation."""
import json
from pathlib import Path
from types import SimpleNamespace

from fastmcp import FastMCP
from pydantic import TypeAdapter
import pytest

from almond_mcp.features.planning.output import encode
from almond_mcp.features.planning.requests import GetRequest, UpdateRequest
from almond_mcp.features.planning.tools import register
from almond_mcp.retrieval_store import AlmondStore
from shared_store import public_result


def test_fresh_session_reads_prior_judgment_and_actually_opens_files(tmp_path, monkeypatch):
    project = tmp_path / 'project'
    project.mkdir()
    source = project / 'source' / 'site-note.md'
    source.parent.mkdir()
    source.write_text('North scheme obstructs the retained entrance.', encoding='utf-8')
    produced = project / '.almond' / 'produced' / 'review' / '01' / 'south-scheme.md'
    produced.parent.mkdir(parents=True)
    produced.write_text('Keep the south access arrangement.', encoding='utf-8')
    outside = tmp_path / 'survey.md'
    outside.write_text('External survey reference.', encoding='utf-8')
    monkeypatch.setenv('ALMOND_PROJECT_ROOT', str(project))
    database = project / 'scene.sqlite3'
    first = AlmondStore(database)
    plan = first.create_plan('Resolve retained entrance', scope='component')
    pid, sid = plan['plan_id'], plan['steps'][0]['step_id']
    tools = register(FastMCP('first-session'), SimpleNamespace(retrieval_store=first))
    refs = ['source/site-note.md', str(outside), str(tmp_path / 'missing-survey.md')]
    decision = '/Keep the south scheme; rejected the north option due to entrance conflict.'
    request = TypeAdapter(UpdateRequest).validate_python({'target': 'step', 'plan_id': pid, 'step_id': sid,
        'input_refs': {'add': refs}, 'output_refs': {'add': [str(produced)]},
        'takeaways': decision, 'design_rationale': 'Preserve access shown in site-note.md.'})
    assert json.loads(tools['update_planning'](request))['changed']
    before = first.get_plan(pid)
    # New store + registered tools simulate the next session; no cached objects.
    second = AlmondStore(database)
    tools = register(FastMCP('fresh-session'), SimpleNamespace(retrieval_store=second))
    query = TypeAdapter(GetRequest).validate_python({'target': 'step', 'plan_id': pid, 'step_id': sid, 'include_details': True})
    body = json.loads(public_result(tools['get_planning'](query), 'get_planning'))['step']
    assert body['input_refs'] == refs and body['output_refs'] == [str(produced)]
    assert body['takeaways'] == decision
    assert (project / body['input_refs'][0]).read_text(encoding='utf-8').startswith('North scheme')
    assert Path(body['input_refs'][1]).read_text(encoding='utf-8').startswith('External survey')
    assert Path(body['output_refs'][0]).read_text(encoding='utf-8').startswith('Keep the south')
    with pytest.raises(OSError):
        Path(body['input_refs'][2]).read_text(encoding='utf-8')
    # A recorded path is still returned when its bytes are unavailable.
    assert second.get_plan(pid) == before


@pytest.mark.parametrize('name', ['get_planning', 'execute_looping', 'get_selection_references'])
def test_nested_current_previous_and_snapshot_records_stay_verbatim(tmp_path, monkeypatch, name):
    monkeypatch.setenv('ALMOND_PROJECT_ROOT', str(tmp_path))
    row = {'input_refs': [r'Z:\source\brief.md'], 'output_refs': [str(tmp_path / 'out.md')],
           'takeaways': '/Absolute-looking judgment', 'design_rationale': r'C:\Decision sentence'}
    payload = {'steps': [row], 'previous_loop': {'steps': [row]}, 'artifact_dir': str(tmp_path / 'produced')}
    result = json.loads(public_result(encode(payload), name))
    assert result['steps'][0] == result['previous_loop']['steps'][0] == row
    assert result['artifact_dir'] == 'produced'
