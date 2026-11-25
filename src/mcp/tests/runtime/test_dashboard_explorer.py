"""User-facing domain reads against disposable producer databases."""
import hashlib
import http.client
import json
import sqlite3
import threading
from urllib.parse import urlencode

import pytest

from dashboard.database import Database
from dashboard.server import DashboardServer
from domain_fixture import add_loop_history_fixture, add_plan_outline_fixture, create_domain_database


@pytest.fixture
def project(tmp_path):
    return Database(create_domain_database(tmp_path / 'project.sqlite3'))


def test_loop_history_uses_recorded_numbers_and_last_revision(project):
    add_loop_history_fixture(project.path)
    before = project.path.read_bytes()
    def task(**options):
        return project.domain_page('tasks', focus='plan_a', **options)['groups'][0]
    assert task()['loop_no'] == 4 and task()['loop_numbers'] == [0, 1, 3, 4]
    assert task()['feedback'] == 'current feedback'
    old = task(loop_no=1)
    assert (old['history'], old['revision'], old['status'], old['name']) == ('snapshot', 2, 'paused', 'Old title')
    assert old['loop_artifact_dir'].endswith('/01')
    assert old['steps'][0]['id'] == 'archived_step' and old['steps'][0]['takeaways'] == 'decision 2'
    detail = project.domain_detail('steps', 'archived_step', 'plan_a', 1)
    assert detail['fields']['output_refs'] == ['previous/deleted.png'] and detail['fields']['loop_no'] == 1
    long_step = old['steps'][1]
    assert long_step['design_rationale']['truncated'] and long_step['output_refs_json'] == ['old/first.png']
    historical_detail = project.domain_detail('steps', 'z_first', 'plan_a', 1)
    assert historical_detail['history'] == 'snapshot' and historical_detail['fields']['output_refs'] == ['old/first.png']
    assert json.loads(project.domain_detail('steps', 'z_first', 'plan_a', 4)['fields']['output_refs_json']) == ['current/new.png']
    assert project.domain_detail('tasks', 'plan_a', loop_no=1)['fields']['goal'] == 'Original goal'
    for pid, number in [('plan_a', 2), ('plan_b', 1), ('plan_a', -1)]:
        with pytest.raises(ValueError):
            project.domain_page('tasks', focus=pid, loop_no=number)
    with pytest.raises(ValueError):
        project.domain_detail('steps', 'm_middle', 'plan_a', 1)
    assert project.path.read_bytes() == before


def test_partial_loop_keeps_feedback_and_migrated_steps_without_current_fields(project):
    add_loop_history_fixture(project.path)
    partial = project.domain_page('tasks', focus='plan_a', loop_no=3)['groups'][0]
    assert partial['history'] == 'partial' and partial['feedback'] == 'feedback only'
    assert not partial['steps'] and partial['status'] is partial['revision'] is partial['goal'] is None
    zero = project.domain_page('tasks', focus='plan_a', loop_no=0)['groups'][0]
    assert zero['history'] == 'partial' and not zero['loop_artifact_dir']
    step = project.domain_detail('steps', 'z_first', 'plan_a', 0)['fields']
    assert step['status'] == 'completed' and json.loads(step['output_refs_json']) == ['장면 해석 결과']
    assert 'name' not in step and 'position' not in step
    assert project.domain_page('tasks', focus='plan_empty')['groups'][0]['loop_numbers'] == []
    with sqlite3.connect(project.path) as db:
        db.execute("UPDATE generation_plan_revisions SET snapshot_json='broken' WHERE revision=2 AND loop_no=1")
    broken = project.domain_page('tasks', focus='plan_a', loop_no=1)
    assert broken['groups'][0]['history'] == 'partial' and broken['groups'][0]['feedback'] == 'first feedback'
    assert broken['notes'] and not broken['groups'][0]['steps']
    with sqlite3.connect(project.path) as db:
        db.execute("UPDATE generation_plan_revisions SET snapshot_json=? WHERE revision=2 AND loop_no=1",
                   (json.dumps({"plan_id": "plan_a", "steps": [{"step_id": "orphan", "status": "failed"}]}),))
    surviving = project.domain_page('tasks', focus='plan_a', loop_no=1)['groups'][0]
    assert surviving['history'] == 'partial' and surviving['status'] is None
    assert surviving['steps'][0]['status'] == 'failed'


def test_step_explorer_reads_current_loop_decisions_and_identity(project):
    with sqlite3.connect(project.path) as db:
        db.execute("UPDATE generation_plans SET loop_no=2 WHERE plan_id='plan_a'")
        db.execute("UPDATE generation_plan_steps SET step_type='reason',name='현재 단계' WHERE plan_id='plan_a' AND step_id='z_first'")
        db.execute("INSERT INTO generation_loop_steps(plan_id,loop_no,step_id,status,takeaways,design_rationale,input_refs_json,output_refs_json) VALUES('plan_a',2,'z_first','running','관찰 기록','판단 이유','[\"도면\"]','[\"검토\"]')")
    before = hashlib.sha256(project.path.read_bytes()).digest()
    page = project.domain_page('steps', parent='plan_a', focus='z_first')
    record = page['groups'][0]
    assert record['id'] == 'z_first' and record['step_type'] == 'reason'
    assert record['name'] == '현재 단계' and record['parent'] == 'plan_a'
    assert record['task'] == {'id': 'plan_a', 'name': '공간 설계'}
    assert record['loop_no'] == 2 and record['status'] == 'running'
    assert record['takeaways'] == '관찰 기록' and record['design_rationale'] == '판단 이유'
    assert json.loads(record['output_refs_json']) == ['검토']
    task = project.domain_page('tasks', focus='plan_a')['groups'][0]
    assert task['steps'][0]['takeaways'] == '관찰 기록'
    detail = project.domain_detail('steps', 'z_first', 'plan_a')['fields']
    assert detail['takeaways'] == '관찰 기록'
    assert hashlib.sha256(project.path.read_bytes()).digest() == before


def test_step_kind_keeps_stored_definition_distinct_from_step_type(project):
    with sqlite3.connect(project.path) as db:
        db.execute("UPDATE generation_plan_steps SET step_type='inspect_03',name='Inspect model' WHERE plan_id='plan_a' AND step_id='z_first'")
    before = hashlib.sha256(project.path.read_bytes()).digest()
    step = project.domain_page('steps', parent='plan_a', focus='z_first')['groups'][0]
    inline = project.domain_page('tasks', focus='plan_a')['groups'][0]['steps'][0]
    for record in (step, inline):
        assert record['kind'] == 'reason'
        assert record['step_type'] == 'inspect_03'
    assert project.domain_detail('steps', 'z_first', 'plan_a')['fields']['kind'] == 'reason'
    assert hashlib.sha256(project.path.read_bytes()).digest() == before


def test_file_explorer_exposes_registered_file_context_and_detail(project):
    with sqlite3.connect(project.path) as db:
        db.execute("INSERT INTO generation_phase_files VALUES ('phase_a','example.3dm',0)")
    page = project.domain_page('files')
    assert page['capabilities']['files']
    file = page['groups'][0]
    assert file['id'] == file['name'] == file['file_name'] == 'example.3dm'
    assert {item['id'] for item in file['scenes']} == {'scene_a', 'scene_b'}
    assert {item['id'] for item in file['holons']} == {'holon_a', 'holon_b', 'holon_child', 'holon_c'}
    assert [item['id'] for item in file['phases']] == ['phase_a']
    assert {item['id'] for item in file['tasks']} == {'plan_a', 'plan_b', 'plan_c', 'plan_empty'}
    assert project.domain_detail('files', 'example.3dm')['fields']['registered'] == 1


def test_task_filters_intersect_actual_multifile_phase_scene_and_expose_options(project):
    with sqlite3.connect(project.path) as db:
        db.execute("INSERT INTO project_files(file_name,registered) VALUES ('other.3dm',1)")
        db.execute("INSERT INTO generation_phase_files VALUES ('phase_a','example.3dm',0)")
        db.execute("INSERT INTO generation_phase_files VALUES ('phase_a','other.3dm',1)")
    page = project.domain_page('tasks', file='other.3dm', phase='phase_a', scene='scene_a')
    assert {item['id'] for item in page['groups']} == {'plan_a', 'plan_b'}
    assert {item['id'] for item in project.domain_page('tasks', file='other.3dm')['groups']} == {'plan_a', 'plan_b', 'plan_empty'}
    assert not project.domain_page('tasks', file='other.3dm', phase='phase_b')['groups']
    assert not project.domain_page('tasks', scene="scene_a' OR 1=1 --")['groups']
    assert page['groups'][0]['phase'] == {'id': 'phase_a', 'name': '설계'}
    assert page['groups'][0]['file_names'] == ['example.3dm', 'other.3dm']
    options = project.domain_options()
    assert options['files'] == [{'id': 'example.3dm', 'name': 'example.3dm'}, {'id': 'other.3dm', 'name': 'other.3dm'}]
    assert [item['id'] for item in options['phases']] == ['phase_a', 'phase_b', 'phase_empty']


def test_task_dropdown_options_intersect_filters_and_keep_literal_search(project):
    with sqlite3.connect(project.path) as db:
        db.execute("INSERT INTO generation_phase_files VALUES ('phase_a','other.3dm',0)")
        db.execute("UPDATE generation_plans SET title='Match A' WHERE plan_id='plan_a'")
        db.execute("UPDATE generation_plans SET title='Match B' WHERE plan_id='plan_b'")
    before = hashlib.sha256(project.path.read_bytes()).digest()
    options = project.domain_options(file='other.3dm', phase='phase_a', scene='scene_b', search='match')
    assert options['tasks'] == [{'id': 'plan_a', 'name': 'Match A'}]
    assert options['files'] and options['phases'] and options['scenes']
    assert not project.domain_options(file='other.3dm', phase='phase_b')['tasks']
    assert not project.domain_options(search="%' OR 1=1 --")['tasks']
    for name in ('file', 'phase', 'scene', 'search'):
        for invalid in ('x' * 201, None, 3):
            with pytest.raises(ValueError):
                project.domain_options(**{name: invalid})
    assert hashlib.sha256(project.path.read_bytes()).digest() == before


def test_task_dropdown_bounds_options_and_explains_truncation(tmp_path):
    path = tmp_path / 'many.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE generation_plans(plan_id TEXT,title TEXT)')
        db.executemany('INSERT INTO generation_plans VALUES (?,?)', [(f'p{i:04}', f'Choice {i:04}') for i in range(2005)])
    database = Database(path)
    before = hashlib.sha256(path.read_bytes()).digest()
    options = database.domain_options()
    assert len(options['tasks']) == 2000
    assert options['tasks'][0] == {'id': 'p0000', 'name': 'Choice 0000'}
    assert options['tasks'][-1]['id'] == 'p1999'
    assert any('tasks:' in note and '2000' in note for note in options['notes'])
    narrowed = database.domain_options(search='Choice 2004')
    assert narrowed['tasks'] == [{'id': 'p2004', 'name': 'Choice 2004'}]
    assert not narrowed['notes']
    assert hashlib.sha256(path.read_bytes()).digest() == before


def test_file_outline_uses_stored_edges_and_excludes_external_parents_from_count(project):
    add_plan_outline_fixture(project.path)
    before = project.path.read_bytes()
    group = project.domain_page('files', focus='other.3dm')['groups'][0]
    items = {item['id']: item for item in group['plan_outline']['items']}
    assert items['outline_root']['file_names'] == ['example.3dm']
    assert not items['outline_root']['matches']
    assert {row['id'] for row in group['tasks']} == {key for key, item in items.items() if item['matches']}
    assert 'outline_next' not in items and 'outline_branch' not in items
    assert items['outline_child_a']['parents'] == items['outline_child_b']['parents'] == ['outline_root']
    assert items['outline_child_b']['previous']['id'] == 'outline_child_a'
    assert items['outline_leaf']['parents'] == ['outline_child_a', 'outline_child_b']
    assert items['outline_loose']['parents'] == [] and items['outline_loose']['previous'] is None
    assert project.domain_options(file='other.3dm')['plan_outline'] == group['plan_outline']
    assert project.path.read_bytes() == before


def test_status_and_execution_filters_keep_only_matches_and_their_ancestors(project):
    add_plan_outline_fixture(project.path)
    filters = dict(file='other.3dm', status='pending', execution='unstarted')
    options = project.domain_options(**filters)
    assert set(options['statuses']) == {'pending', 'running', 'paused', 'completed', 'failed', 'blocked'}
    assert options['has_execution_history'] is True
    assert [item['id'] for item in options['tasks']] == ['outline_leaf']
    assert {item['id']: item['matches'] for item in options['plan_outline']['items']} == {
        'outline_root': False, 'outline_child_a': False, 'outline_child_b': False, 'outline_leaf': True,
    }
    assert [row['id'] for row in project.domain_page('tasks', **filters)['groups']] == ['outline_leaf']
    without_execution = project.domain_options(file='other.3dm', status='pending')['tasks']
    assert {'outline_leaf', 'outline_pending', 'outline_legacy'} <= {item['id'] for item in without_execution}
    assert 'outline_loose' in {row['id'] for row in project.domain_options(file='other.3dm', execution='unstarted')['tasks']}
    assert not project.domain_options(status='not_started')['tasks']
    with pytest.raises(ValueError, match='실행 이력 필터'):
        project.domain_options(execution='pending')


def test_task_relations_keep_types_and_report_dangling_without_recursive_expansion(project):
    with sqlite3.connect(project.path) as db:
        db.execute("UPDATE generation_plans SET previous_id='plan_b',depends_on_json='[\"plan_b\",\"missing\",\"plan_a\"]',parent_plan_json='[\"plan_c\"]',child_plan_json='[\"plan_empty\"]' WHERE plan_id='plan_a'")
        db.execute("UPDATE generation_plans SET previous_id='plan_a',depends_on_json='[\"plan_a\"]' WHERE plan_id='plan_b'")
    record = project.domain_page('tasks', focus='plan_a')['groups'][0]
    relations = {(item['type'], item['id']): item for item in record['relations']}
    assert ('previous', 'plan_b') in relations and ('next', 'plan_b') in relations
    assert [item['id'] for item in record['relations'] if item['type'] == 'related'].count('plan_b') == 1
    assert ('parent', 'plan_c') in relations and ('child', 'plan_empty') in relations
    assert relations['related', 'missing']['missing'] is True
    assert relations['related', 'missing']['name'] == '미등록 Task'
    assert relations['related', 'plan_a']['missing'] is False
    parent = project.domain_page('tasks', focus='plan_c')['groups'][0]
    child = project.domain_page('tasks', focus='plan_empty')['groups'][0]
    assert ('child', 'plan_a') in {(r['type'], r['id']) for r in parent['relations']}
    assert ('parent', 'plan_a') in {(r['type'], r['id']) for r in child['relations']}
    assert len(record['steps']) == 3


def test_task_page_uses_each_tasks_own_links_even_outside_reverse_lookup_limit(project, monkeypatch):
    monkeypatch.setattr('dashboard.domain_views.LINK_LIMIT', 2)
    with sqlite3.connect(project.path) as db:
        db.execute("UPDATE generation_plans SET depends_on_json=? WHERE plan_id='plan_a'",
                   (json.dumps([{}, None, 'plan_c', 'plan_c']),))
        db.execute("UPDATE generation_plans SET previous_id='plan_empty' WHERE plan_id='plan_b'")
        db.execute("UPDATE generation_plans SET parent_plan_json=? WHERE plan_id='plan_c'",
                   (json.dumps(['plan_empty']),))
    page = project.domain_page('tasks')
    links = {row['id']: [(link['type'], link['id']) for link in row['relations']] for row in page['groups']}
    assert links['plan_c'].count(('related', 'plan_a')) == 1
    assert ('parent', 'plan_empty') in links['plan_c']
    assert ('next', 'plan_b') in links['plan_empty']
    assert ('child', 'plan_c') not in links['plan_empty']
    assert any('처음 2개 기록' in note for note in page['notes'])


def test_missing_loop_is_reported_before_decoding_other_task_relations(tmp_path):
    path = tmp_path / 'legacy.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE generation_plans(plan_id,previous_id,loop_no)")
        db.executemany("INSERT INTO generation_plans VALUES(?,?,1)", [('p', None), (b'legacy', 'p')])
    with pytest.raises(ValueError, match='선택한 회차 기록이 없습니다'):
        Database(path).domain_page('tasks', focus='p', loop_no=5)


@pytest.mark.parametrize('canonical_state', ['populated', 'empty', 'partial'])
def test_holon_scene_filter_uses_canonical_relationships_and_intersects_file(project, canonical_state):
    with sqlite3.connect(project.path) as db:
        db.execute("CREATE TABLE scene_components(scene_id TEXT,component_id TEXT)")
        db.execute("INSERT INTO scene_components VALUES ('scene_b','holon_a')")
        db.execute("ALTER TABLE ontological_holons ADD COLUMN scene_ids_json TEXT")
        db.execute("UPDATE ontological_holons SET scene_ids_json='[\"scene_b\"]'")
        db.execute("UPDATE ontological_holons SET file_name='other.3dm' WHERE ontological_id='holon_b'")
        for table in ('ontological_scene_context', 'scene_ontological'):
            if canonical_state == 'empty':
                db.execute(f'DELETE FROM {table}')
            elif canonical_state == 'partial':
                db.execute(f'DROP TABLE {table}')
                db.execute(f'CREATE TABLE {table}(scene_id TEXT)')
    before = hashlib.sha256(project.path.read_bytes()).digest()
    page = project.domain_page('holons', file='example.3dm', scene='scene_a')
    expected = {'holon_a', 'holon_child'} if canonical_state == 'populated' else set()
    assert {row['id'] for row in page['groups']} == expected
    assert not project.domain_page('holons', file='example.3dm', scene="scene_a' OR 1=1 --")['groups']
    assert {row['id'] for row in project.domain_page('holons', scene='scene_b')['groups']} == ({'holon_c'} if canonical_state == 'populated' else set())
    if canonical_state == 'partial':
        assert page['notes']
    assert hashlib.sha256(project.path.read_bytes()).digest() == before


@pytest.mark.parametrize('source', ['legacy', 'json', 'missing'])
def test_holon_scene_filter_supports_legacy_or_stored_array_only_without_canonical(project, source):
    with sqlite3.connect(project.path) as db:
        db.execute('DROP TABLE ontological_scene_context')
        db.execute('DROP TABLE scene_ontological')
        if source != 'missing':
            db.execute('ALTER TABLE ontological_holons ADD COLUMN scene_ids_json TEXT')
            db.execute("UPDATE ontological_holons SET scene_ids_json='not json'")
        if source == 'legacy':
            db.execute('CREATE TABLE scene_components(scene_id TEXT,component_id TEXT)')
            db.execute("INSERT INTO scene_components VALUES ('scene_a','holon_c')")
            db.execute("UPDATE ontological_holons SET scene_ids_json='[\"scene_a\"]' WHERE ontological_id='holon_a'")
        elif source == 'json':
            db.execute("UPDATE ontological_holons SET scene_ids_json='[\"scene_a\",\"scene_b\"]' WHERE ontological_id='holon_c'")
            db.execute("UPDATE ontological_holons SET scene_ids_json='{\"scene\":\"scene_a\"}' WHERE ontological_id='holon_a'")
    before = hashlib.sha256(project.path.read_bytes()).digest()
    schema = project.schema()
    orphan = next(view for view in schema["tables"] if view["name"] == "_scene_component_refs")
    assert orphan["type"] == "view" and orphan["readable"] is False
    assert schema["domain_views"]["holons"]
    page = project.domain_page('holons', file='example.3dm', scene='scene_a')
    assert any("_scene_component_refs" in note for note in page["notes"])
    assert [row['id'] for row in page['groups']] == ([] if source == 'missing' else ['holon_c'])
    assert not project.domain_page('holons', file='other.3dm', scene='scene_a')['groups']
    if source == 'missing':
        assert page['notes']
    assert hashlib.sha256(project.path.read_bytes()).digest() == before


def test_phase_and_scene_file_filters_use_stored_relationships(project):
    with sqlite3.connect(project.path) as db:
        db.execute("INSERT INTO generation_phase_files VALUES ('phase_a','other.3dm',0)")
        db.execute("UPDATE scenes SET file_name='other.3dm' WHERE scene_id='scene_b'")
    assert [row['id'] for row in project.domain_page('phases', file='other.3dm')['groups']] == ['phase_a']
    assert [row['id'] for row in project.domain_page('scenes', file='other.3dm')['groups']] == ['scene_b']
    assert not project.domain_page('phases', file='absent.3dm')['groups']
    assert not project.domain_page('scenes', file="x' OR 1=1 --")['groups']


def test_six_domain_http_reads_keep_authentication_identity_and_database_bytes(project):
    before = hashlib.sha256(project.path.read_bytes()).digest()
    server = DashboardServer(project.path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(route, params=None, authenticated=True, method='GET'):
        client = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        client.request(method, route + ('?' + urlencode(params) if params else ''),
                       headers={'X-Dashboard-Token': server.token} if authenticated else {})
        response = client.getresponse()
        result = response.status, json.loads(response.read())
        client.close()
        return result

    try:
        params = {'database': str(project.path)}
        assert request('/api/domain-options', params, False)[0] == 403
        assert request('/api/domain-options', {'database': 'other'})[0] == 409
        assert request('/api/domain-options', params)[1]['files'][0]['id'] == 'example.3dm'
        status, body = request('/api/domain-options', {**params, 'file': 'example.3dm', 'phase': 'phase_a', 'scene': 'scene_b', 'search': 'house'})
        assert status == 200 and [row['id'] for row in body['tasks']] == ['plan_a']
        filters = {**params, 'status': 'pending', 'execution': 'unstarted'}
        status, body = request('/api/domain-options', filters)
        assert status == 200 and [row['id'] for row in body['tasks']] == ['plan_unassigned']
        status, body = request('/api/domain', {**filters, 'view': 'tasks'})
        assert status == 200 and [row['id'] for row in body['groups']] == ['plan_unassigned']
        assert request('/api/domain-options', {**params, 'execution': 'invalid'})[0] == 400
        for name in ('file', 'phase', 'scene', 'search'):
            assert request('/api/domain-options', {**params, name: 'x' * 201})[0] == 400
        for kind in ('files', 'scenes', 'holons', 'phases', 'tasks', 'steps'):
            status, body = request('/api/domain', {**params, 'view': kind})
            assert status == 200 and body['groups']
        status, body = request('/api/domain', {**params, 'view': 'tasks', 'phase': 'phase_a', 'scene': 'scene_a'})
        assert status == 200 and {row['id'] for row in body['groups']} == {'plan_a', 'plan_b'}
        assert request('/api/domain-options', method='POST')[0] == 404
    finally:
        server.shutdown(); server.server_close(); thread.join(2)
    assert hashlib.sha256(project.path.read_bytes()).digest() == before


def test_step_pages_beyond_task_expansion_are_still_current_and_parent_scoped(project):
    with sqlite3.connect(project.path) as db:
        db.executemany("INSERT INTO generation_plan_steps(plan_id,step_id,position,kind,step_type,name,depends_on_json) VALUES ('plan_empty',?,?,'reason','reason',?,'[]')",
                       [(f'uuid_{i:03}', i, f'단계 {i}') for i in range(220)])
        db.execute("INSERT INTO generation_loop_steps(plan_id,loop_no,step_id,status,takeaways) VALUES ('plan_empty',0,'uuid_210','completed','현재 회차 기록')")
    page = project.domain_page('steps', parent='plan_empty', offset=210, limit=1)
    assert page['has_more'] and page['groups'][0]['id'] == 'uuid_210'
    assert page['groups'][0]['takeaways'] == '현재 회차 기록'
    assert not project.domain_page('steps', parent='plan_a', focus='uuid_210')['groups']
    with pytest.raises(ValueError):
        project.domain_detail('steps', 'uuid_210', 'plan_a')
