"""Retire the per-object SQL ledger while retaining semantic registrations."""
from __future__ import annotations

import json
import sqlite3
import uuid


def initialize_group_summaries(store, connection):
    if not connection.in_transaction:
        connection.execute('BEGIN IMMEDIATE')
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    legacy = 'document_objects' in tables
    populated = any(connection.execute(f'SELECT 1 FROM {table} LIMIT 1').fetchone()
                    for table in ('components','scenes','generation_plans','generation_phases','document_objects') if table in tables)
    if populated:
        # A separate reader sees the committed pre-migration DB while this writer
        # holds the reservation against concurrent writes. Never overwrite a backup.
        archive = store.database_path.with_name(store.database_path.name + '.before-object-retirement-' + uuid.uuid4().hex + '.bak')
        with sqlite3.connect(store.database_path) as source, sqlite3.connect(archive) as target:
            source.backup(target)
    columns = {row['name'] for row in connection.execute('PRAGMA table_info(components)')}
    for name, declaration in {
        'geometry_digest': "TEXT NOT NULL DEFAULT ''",
        'object_count': 'INTEGER NOT NULL DEFAULT 0',
        'effective_object_count': 'INTEGER NOT NULL DEFAULT 0',
        'object_types_json': "TEXT NOT NULL DEFAULT '{}'",
        'bounds_json': "TEXT NOT NULL DEFAULT 'null'",
    }.items():
        if name not in columns:
            connection.execute(f'ALTER TABLE components ADD COLUMN {name} {declaration}')
    if not legacy:
        return
    objects = {}
    for row in connection.execute('SELECT * FROM document_objects WHERE component_id IS NOT NULL'):
        objects.setdefault(row['component_id'], []).append(dict(
            rhino_guid=row['rhino_guid'], component_id=row['component_id'], object_type=row['object_type'],
            name=row['name'] if 'name' in row.keys() else '',
            bounds_mm=[float(row[key]) for key in ('min_x','min_y','min_z','max_x','max_y','max_z')]))
    for row in connection.execute('SELECT component_id, availability FROM components').fetchall():
        direct = objects.get(row['component_id'], []) if row['availability'] == 'present' else []
        descendants = [r[0] for r in connection.execute("""WITH RECURSIVE subtree(component_id) AS (
            SELECT component_id FROM components WHERE component_id=? UNION
            SELECT c.component_id FROM components c JOIN subtree p ON c.parent_component_id=p.component_id)
            SELECT component_id FROM subtree""",(row['component_id'],))]
        effective = [obj for handle in descendants for obj in objects.get(handle, [])] if row['availability'] == 'present' else []
        summary = store._component_summary(direct, effective)
        connection.execute('UPDATE components SET geometry_digest=?,object_count=?,effective_object_count=?,object_types_json=?,bounds_json=? WHERE component_id=?',
            (summary['geometry_digest'],summary['object_count'],summary['effective_object_count'],
             json.dumps(summary['object_types']),json.dumps(summary['bounds_mm']),row['component_id']))
    # Old component/direct-Scene revisions stored member IDs. The external backup
    # preserves history; the active ledger retains only the semantic revision.
    for row in connection.execute('SELECT scene_id,revision,patch_json FROM scene_revisions').fetchall():
        patch = json.loads(row['patch_json'])
        if isinstance(patch, dict) and 'object_ids' in patch:
            patch.pop('object_ids')
            connection.execute('UPDATE scene_revisions SET patch_json=? WHERE scene_id=? AND revision=?',
                (json.dumps(patch),row['scene_id'],row['revision']))
    connection.execute('DROP TABLE IF EXISTS scene_objects')
    connection.execute('DROP TABLE document_objects')
