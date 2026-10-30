"""A pre-semantic-schema database, independent of current initialization code."""
from almond_mcp.retrieval_store import AlmondStore


def legacy_store(path):
    store = AlmondStore.__new__(AlmondStore)
    store.database_path = path
    scene, model = 'scene_old', str(path.parent / 'model.3dm')
    with store._connect() as db:
        db.executescript('''
            CREATE TABLE scenes(scene_id TEXT PRIMARY KEY,name TEXT NOT NULL,units TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,file_name TEXT NOT NULL DEFAULT '');
            CREATE TABLE components(component_id TEXT PRIMARY KEY,model_path TEXT NOT NULL,rhino_group_id TEXT NOT NULL,
                name TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                parent_component_id TEXT REFERENCES components(component_id) ON DELETE RESTRICT,
                UNIQUE(component_id,model_path),UNIQUE(model_path,rhino_group_id));
            CREATE TABLE scene_components(scene_id TEXT REFERENCES scenes(scene_id),component_id TEXT REFERENCES components(component_id),PRIMARY KEY(scene_id,component_id));
        ''')
        db.execute("INSERT INTO scenes VALUES(?,'Kept','mm',0,'2026-01-01T00:00:42+00:00','2026-01-01T00:00:42+00:00','model.3dm')",(scene,))
        db.execute("INSERT INTO components VALUES('component_old',?,'00000000-0000-0000-0000-000000000100','Old','2026-01-01T00:00:42+00:00','2026-01-01T00:00:42+00:00',NULL)",(model,))
        db.execute("INSERT INTO scene_components VALUES(?,'component_old')",(scene,))
    return store, scene, model
