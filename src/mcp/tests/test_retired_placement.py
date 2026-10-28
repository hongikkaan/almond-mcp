"""Retired room/instance APIs leave existing user records intact."""
from almond_mcp.retrieval_store import AlmondStore


def seed_legacy_placement(store, scene_id, asset_id):
    with store._connect() as connection:
        values = {'instance_id': 'legacy-instance', 'scene_id': scene_id, 'asset_id': asset_id,
                  'metadata_json': '{}', 'created_at': 'old', 'updated_at': 'old', 'scale': 1}
        for row in connection.execute('PRAGMA table_info(instances)'):
            if row['name'] not in values and row['notnull'] and row['dflt_value'] is None:
                values[row['name']] = 0
        columns = ','.join(values)
        placeholders = ','.join('?' for _ in values)
        connection.execute(f'INSERT INTO instances ({columns}) VALUES ({placeholders})', list(values.values()))


def test_reopening_legacy_ledger_preserves_data_without_restoring_retired_apis(tmp_path):
    path = tmp_path / 'scene.sqlite3'
    store = AlmondStore(path)
    scene = store.create_scene('Preserved scene')['scene_id']
    store.sync_assets([{'asset_id': 'fixture', 'dimensions_mm': {'width': 1, 'depth': 1, 'height': 1}}], library_id='fixture')
    seed_legacy_placement(store, scene, 'fixture')
    with store._connect() as connection:
        connection.execute("INSERT INTO rooms VALUES ('legacy-room', ?, 'Room', 0, 1, 0, 1, 0, 1, '{}', 'old', 'old')", (scene,))
        before = {table: [tuple(row) for row in connection.execute('SELECT * FROM '+table)]
                  for table in ('rooms', 'instances', 'scene_revisions')}
    reopened = AlmondStore(path)
    with reopened._connect() as connection:
        after = {table: [tuple(row) for row in connection.execute('SELECT * FROM '+table)] for table in before}
    assert after == before
    assert not {'rooms', 'instances'} & reopened.get_scene(scene).keys()
    for method in ('upsert_room','remove_room','upsert_instance','remove_instance','scene_instances','validate_scene'):
        assert not hasattr(reopened, method)
