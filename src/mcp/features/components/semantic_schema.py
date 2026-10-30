"""Canonical semantic tables and transactional migration from the legacy ledger."""
from __future__ import annotations

import json

from almond_mcp.features.components.schema import initialize_group_summaries


def initialize_semantics(store, connection):
    if not connection.in_transaction:
        connection.execute('BEGIN IMMEDIATE')
    tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    legacy = 'components' in tables
    if legacy and 'ontological_components' in tables:
        raise RuntimeError('Mixed legacy and semantic schemas. Stop older clients and inspect the DB before continuing.')
    if not legacy and {'document_objects', 'scene_objects'} & tables:
        raise RuntimeError('Object tables without the legacy semantic registry cannot be migrated safely. Stop older clients and inspect the DB.')
    if legacy:
        columns = {r['name'] for r in connection.execute('PRAGMA table_info(components)')}
        if 'availability' not in columns:
            connection.execute("ALTER TABLE components ADD COLUMN availability TEXT NOT NULL DEFAULT 'present'")
        if 'parent_component_id' not in columns:
            connection.execute('ALTER TABLE components ADD COLUMN parent_component_id TEXT REFERENCES components(component_id) ON DELETE RESTRICT')
        if 'scene_ids_json' not in columns:
            connection.execute("ALTER TABLE components ADD COLUMN scene_ids_json TEXT NOT NULL DEFAULT '[]'")
            if 'scene_components' in tables:
                for r in connection.execute('SELECT component_id FROM components').fetchall():
                    ids = [s[0] for s in connection.execute('SELECT scene_id FROM scene_components WHERE component_id=? ORDER BY scene_id',(r[0],))]
                    connection.execute('UPDATE components SET scene_ids_json=? WHERE component_id=?',(json.dumps(ids),r[0]))
        initialize_group_summaries(store,connection)
        store._retire_drawing_sheet_constraints(connection)
    connection.execute('''CREATE TABLE IF NOT EXISTS project_files(file_id TEXT NOT NULL PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
        file_name TEXT NOT NULL CHECK(length(trim(file_name))>0 AND file_name NOT IN ('.','..')
        AND instr(file_name,'/')=0 AND instr(file_name,char(92))=0 AND instr(file_name,':')=0))''')
    connection.execute('''CREATE TABLE IF NOT EXISTS _project_file_locations(
        file_id TEXT PRIMARY KEY REFERENCES project_files(file_id) ON DELETE RESTRICT,
        model_path TEXT NOT NULL UNIQUE)''')
    connection.execute('''CREATE TABLE IF NOT EXISTS ontological_components(
        ontological_id TEXT PRIMARY KEY,
        project_file_id TEXT NOT NULL REFERENCES project_files(file_id) ON DELETE RESTRICT,
        rhino_group_id TEXT NOT NULL,name TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
        parent_ontological_id TEXT REFERENCES ontological_components(ontological_id) ON DELETE RESTRICT,
        availability TEXT NOT NULL DEFAULT 'present' CHECK(availability IN ('present','missing_group','unregistered')),
        geometry_digest TEXT NOT NULL DEFAULT '',
        object_count INTEGER NOT NULL DEFAULT 0,effective_object_count INTEGER NOT NULL DEFAULT 0,
        effective_summary_stale INTEGER NOT NULL DEFAULT 0 CHECK(effective_summary_stale IN (0,1)),
        object_types_json TEXT NOT NULL DEFAULT '{}',bounds_json TEXT NOT NULL DEFAULT 'null',
        UNIQUE(project_file_id,rhino_group_id))''')
    connection.execute('''CREATE TABLE IF NOT EXISTS ontological_scene_context(
        ontological_id TEXT NOT NULL REFERENCES ontological_components(ontological_id) ON DELETE CASCADE,
        scene_id TEXT NOT NULL REFERENCES scenes(scene_id) ON DELETE RESTRICT,
        PRIMARY KEY(ontological_id,scene_id))''')
    connection.execute('''CREATE TABLE IF NOT EXISTS scene_ontological(
        scene_id TEXT NOT NULL REFERENCES scenes(scene_id) ON DELETE CASCADE,
        ontological_id TEXT NOT NULL REFERENCES ontological_components(ontological_id) ON DELETE CASCADE,
        PRIMARY KEY(scene_id,ontological_id))''')
    connection.execute('''CREATE TABLE IF NOT EXISTS generation_plan_ontological(
        plan_id TEXT NOT NULL REFERENCES generation_plans(plan_id) ON DELETE CASCADE,
        ontological_id TEXT NOT NULL REFERENCES ontological_components(ontological_id) ON DELETE RESTRICT,
        position INTEGER NOT NULL,PRIMARY KEY(plan_id,ontological_id),UNIQUE(plan_id,position))''')
    connection.execute('''CREATE TABLE IF NOT EXISTS generation_step_ontological(
        plan_id TEXT NOT NULL,step_id TEXT NOT NULL,
        ontological_id TEXT NOT NULL REFERENCES ontological_components(ontological_id) ON DELETE RESTRICT,
        position INTEGER NOT NULL,PRIMARY KEY(plan_id,step_id,ontological_id),UNIQUE(plan_id,step_id,position),
        FOREIGN KEY(plan_id,step_id) REFERENCES generation_plan_steps(plan_id,step_id) ON DELETE CASCADE)''')
    if legacy:
        records = connection.execute('SELECT * FROM components').fetchall()
        for r in records:
            file_id = store._project_file_reference(connection,model_path=r['model_path'])
            connection.execute('''INSERT INTO ontological_components(ontological_id,project_file_id,rhino_group_id,
                name,created_at,updated_at,availability,geometry_digest,object_count,effective_object_count,object_types_json,bounds_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                (r['component_id'],file_id,r['rhino_group_id'],r['name'],r['created_at'],r['updated_at'],r['availability'],
                 r['geometry_digest'],r['object_count'],r['effective_object_count'],r['object_types_json'],r['bounds_json']))
            connection.executemany('INSERT INTO ontological_scene_context VALUES(?,?)',
                [(r['component_id'],scene) for scene in json.loads(r['scene_ids_json'])])
        for r in records:
            connection.execute('UPDATE ontological_components SET parent_ontological_id=? WHERE ontological_id=?',
                (r['parent_component_id'],r['component_id']))
        for old,new,fields in [('scene_components','scene_ontological','scene_id,component_id'),
                ('generation_plan_components','generation_plan_ontological','plan_id,component_id,position'),
                ('generation_step_components','generation_step_ontological','plan_id,step_id,component_id,position')]:
            if old in tables:
                connection.execute(f'INSERT INTO {new} SELECT {fields} FROM {old}')
                connection.execute(f'DROP TABLE {old}')
        connection.execute('UPDATE components SET parent_component_id=NULL')
        connection.execute('DROP TABLE components')
    # Read projections preserve the public/native component_id vocabulary. All
    # relationships and writes use the canonical ontological IDs in real tables.
    connection.execute('''CREATE VIEW IF NOT EXISTS _component_records AS SELECT
        c.ontological_id AS component_id,l.model_path,c.project_file_id,f.file_name,c.rhino_group_id,c.name,
        c.created_at,c.updated_at,c.parent_ontological_id AS parent_component_id,c.availability,
        (SELECT json_group_array(scene_id) FROM (SELECT scene_id FROM ontological_scene_context
            WHERE ontological_id=c.ontological_id ORDER BY scene_id)) AS scene_ids_json,
        c.geometry_digest,c.object_count,c.effective_object_count,c.effective_summary_stale,c.object_types_json,c.bounds_json
        FROM ontological_components c JOIN project_files f ON f.file_id=c.project_file_id
        LEFT JOIN _project_file_locations l ON l.file_id=c.project_file_id''')
    for view,table,fields in [('_scene_component_refs','scene_ontological','scene_id,ontological_id AS component_id'),
            ('_plan_component_refs','generation_plan_ontological','plan_id,ontological_id AS component_id,position'),
            ('_step_component_refs','generation_step_ontological','plan_id,step_id,ontological_id AS component_id,position')]:
        connection.execute(f'CREATE VIEW IF NOT EXISTS {view} AS SELECT {fields} FROM {table}')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_ontological_parent ON ontological_components(parent_ontological_id)')
    for action,suffix in [('INSERT','insert'),('UPDATE OF parent_ontological_id,project_file_id','update')]:
        connection.execute(f'''CREATE TRIGGER IF NOT EXISTS ontological_parent_check_{suffix}
            BEFORE {action} ON ontological_components WHEN NEW.parent_ontological_id IS NOT NULL
            BEGIN
                SELECT CASE WHEN NEW.parent_ontological_id=NEW.ontological_id OR NOT EXISTS(
                    SELECT 1 FROM ontological_components p WHERE p.ontological_id=NEW.parent_ontological_id
                    AND p.project_file_id=NEW.project_file_id)
                THEN RAISE(ABORT,'Semantic parent must exist in the same model and differ from child') END;
                SELECT CASE WHEN EXISTS(WITH RECURSIVE ancestors(ontological_id,parent_ontological_id) AS (
                    SELECT ontological_id,parent_ontological_id FROM ontological_components WHERE ontological_id=NEW.parent_ontological_id
                    UNION SELECT c.ontological_id,c.parent_ontological_id FROM ontological_components c
                    JOIN ancestors a ON c.ontological_id=a.parent_ontological_id)
                    SELECT 1 FROM ancestors WHERE ontological_id=NEW.ontological_id)
                THEN RAISE(ABORT,'Semantic hierarchy contains a cycle') END;
            END''')
    if connection.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('Semantic migration found an invalid relationship; the migration was rolled back.')


def initialize_file_relations(store,connection):
    for table in ('scenes','generation_phases'):
        columns = {r['name'] for r in connection.execute(f'PRAGMA table_info({table})')}
        if 'project_file_id' not in columns:
            connection.execute(f'ALTER TABLE {table} ADD COLUMN project_file_id TEXT REFERENCES project_files(file_id) ON DELETE RESTRICT')
        if 'file_name' in columns:
            key = 'scene_id' if table=='scenes' else 'phase_id'
            for row in connection.execute(f'SELECT {key},file_name FROM {table}').fetchall():
                file_id = store._project_file_reference(connection,row['file_name'])
                connection.execute(f'UPDATE {table} SET project_file_id=? WHERE {key}=?',(file_id,row[key]))
            connection.execute(f'ALTER TABLE {table} DROP COLUMN file_name')
        view = '_scene_records' if table == 'scenes' else '_phase_records'
        connection.execute(f'''CREATE VIEW IF NOT EXISTS {view} AS SELECT s.*,COALESCE(f.file_name,'') AS file_name
            FROM {table} s LEFT JOIN project_files f ON f.file_id=s.project_file_id''')
