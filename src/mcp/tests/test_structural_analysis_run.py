"""A panel study shares solved states while retaining 11/13-point projections."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from almond_mcp.features.structure import native_structure as ns, structure_study as study


def model(column=False):
    end = [0, 0, 3] if column else [3, 0, 0]
    return dict(status='ok', shells=0, tolerance_m=.001, max_member_span_m=3., max_span_m=3.,
                anchor_points=[[0, 0, 0]], members=[dict(source_guids=['member'],
                points=[[0, 0, 0], end], section=dict(shape='solid_rectangle', width=.1, height=.1))])


def without_timing(result):
    result = deepcopy(result)
    result.get('results', {}).pop('solve_ms', None)
    return result


@pytest.mark.parametrize('column,stability,load,view', [
    (False, 'off', 1., 'deflection'), (False, 'auto', 1., 'deflection'),
    (True, 'auto', 10., 'deflection'), (True, 'auto', 100., 'deflection'),
    (True, 'auto', 10000., 'deflection'), (True, 'auto', 10., 'buckling'),
    (True, 'auto', 10000., 'buckling'),
])
def test_panel_preserves_independent_validation_and_view(column, stability, load, view):
    source = model(column)
    common = dict(stability=stability, self_weight=True, uls='6.10ab', connections='rigid')
    baseline = ns.validate(source, 'frame', load, detail=True, **common)
    try:
        expected, span = ns.view_result(source, load, view=view,
                                       span_m=baseline['results'].get('span_m'), **common)
    except (ns.InstabilityError, ns.fs.MechanismError, ValueError):
        expected = None
    with patch.object(ns, '_solve_design', wraps=ns._solve_design) as solve:
        result = study.run(dict(model=source, settings=dict(load_kn=load, stability=stability,
                           self_weight=True, view=view, uls_combination='6.10ab')))
    assert without_timing(result['validation']) == without_timing(baseline)
    if expected is not None:
        assert result['draw']['result']['elements'] == expected['elements']
        assert result['draw']['result']['max_displacement_mm'] == expected['max_displacement_mm']
        assert all(len(e['samples_m']) == 13 for e in result['draw']['result']['elements'])
        assert result.get('buckling') == expected.get('buckling')
    else:
        assert 'draw' not in result
    assert solve.call_count == (2 if view == 'buckling' else 1)


def test_panel_rejects_invalid_model_without_calculation():
    with patch.object(ns, '_solve_design', wraps=ns._solve_design) as solve:
        result = study.run(dict(model=dict(status='ok', members=[])))
    assert result['status'] == 'error'
    solve.assert_not_called()


def test_distinct_station_grids_do_not_reuse_validation_sample_maximum():
    source = model()
    source['anchor_points'] = [[0,0,0], [2,0,0], [5,0,0]]
    source['members'] = [dict(source_guids=[str(i)], points=[a,b],
        section=dict(shape='solid_rectangle', width=.1, height=.1)) for i,(a,b) in enumerate([
            ([0,0,0],[2,0,0]), ([2,0,0],[5,0,0])])]
    options = dict(load_kn=0, stability='off', fixed_supports=False, self_weight=True)
    validation = ns.validate(source, detail=True, **options)
    view, _ = ns.view_result(source, **options)
    assert validation['results']['max_deflection_mm'] != view['max_displacement_mm']
    result = study.run(dict(model=source, settings=dict(load_kn=0, stability='off',
                           fixed_rotations=False, self_weight=True)))
    assert result['validation']['results']['max_deflection_mm'] == validation['results']['max_deflection_mm']
    assert result['draw']['result']['max_displacement_mm'] == view['max_displacement_mm']
    assert result['draw']['result']['elements'] == view['elements']


def test_history_persists_applied_native_options_and_result(tmp_path):
    from test_stage2_structure import StructureTools, OPTIONS
    api = StructureTools(tmp_path / 'history.sqlite3')
    result = api.call('validate_structure', guids=['beam'], engine='native', span_m=4,
                      design_basis='en1990', uls_combination='6.10ab', fabrication='hot_finished',
                      detail=True, **OPTIONS)
    from almond_mcp.retrieval_store import AlmondStore
    store = AlmondStore(tmp_path / 'history.sqlite3')
    run = store.list_validation_runs()[0]
    assert run['request']['engine'] == 'native'
    assert run['request']['stability'] == 'off'
    assert run['request']['span_m'] == 4
    assert run['analysis']['inputs']['fabrication'] == 'hot_finished'
    assert run['analysis']['inputs']['validation_stations'] == 11
    assert run['analysis']['engine'] == 'native'
    assert run['analysis']['inputs']['model'] == api.model
    assert run['result'] == {k: v for k, v in result.items() if k != 'next_step_guide'}


@pytest.mark.parametrize('modern', [False, True])
def test_history_snapshot_migration_rolls_back_with_late_constructor_failure(tmp_path, modern):
    import sqlite3
    from test_stage2_structure import seed_legacy_history
    from almond_mcp.retrieval_store import AlmondStore
    database = tmp_path / 'migration.sqlite3'
    seed_legacy_history(database)
    if modern:
        # Current pre-snapshot schema, including nullable verdict and explicit status.
        with sqlite3.connect(database) as db:
            sql = db.execute("SELECT sql FROM sqlite_schema WHERE name='validation_runs'").fetchone()[0]
            sql = sql.replace('validation_runs', 'modern_runs').replace('passed INTEGER NOT NULL', 'passed INTEGER')
            db.execute(sql)
            db.execute('INSERT INTO modern_runs SELECT * FROM validation_runs')
            db.execute('DROP TABLE validation_runs')
            db.execute('ALTER TABLE modern_runs RENAME TO validation_runs')
            db.execute("ALTER TABLE validation_runs ADD COLUMN status TEXT NOT NULL DEFAULT 'pass'")
    def snapshot():
        with sqlite3.connect(database) as db:
            return list(db.iterdump())
    original = snapshot()
    with patch('almond_mcp.features.components.semantic_schema.initialize_semantics',
               side_effect=RuntimeError('late migration failure')):
        with pytest.raises(RuntimeError, match='late migration failure'):
            AlmondStore(database)
    assert snapshot() == original
    runs = AlmondStore(database).list_validation_runs()
    assert len(runs) == 2
    assert all(r['analysis'] is None and r['request'] is None and r['result'] is None for r in runs)
