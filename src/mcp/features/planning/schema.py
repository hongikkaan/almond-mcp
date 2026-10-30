"""Controlled workflow vocabulary and migrations that preserve dependent rows."""
from __future__ import annotations

import re
from datetime import datetime

STATUSES = ('pending', 'running', 'completed', 'failed', 'blocked', 'paused')
SCOPES = ('house', 'interior', 'structure', 'drawing', 'component')


def _add_reference(connection, table, column, target, key):
    if any(row['from'] == column and row['table'] == target
           for row in connection.execute(f'PRAGMA foreign_key_list({table})')):
        return
    # Called only by initialization with foreign keys disabled before BEGIN.
    # Copy every column, index and trigger, then verify all FKs before commit.
    if connection.execute('PRAGMA foreign_keys').fetchone()[0]:
        raise RuntimeError('Schema rebuilding requires the initialization transaction.')
    sql = connection.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name=?', (table,)).fetchone()[0]
    extras = [r[0] for r in connection.execute(
        'SELECT sql FROM sqlite_master WHERE tbl_name=? AND type IN ("index","trigger") AND sql IS NOT NULL', (table,))]
    temporary = '_migrate_' + table
    sql = re.sub(r'^(CREATE TABLE\s+)(?:"?' + re.escape(table) + r'"?)', r'\g<1>' + temporary, sql, count=1, flags=re.I)
    sql, count = re.subn(r'\b' + re.escape(column) + r'\s+TEXT\s+NOT\s+NULL\b',
                         f'{column} TEXT NOT NULL REFERENCES {target}({key}) ON DELETE RESTRICT', sql, count=1, flags=re.I)
    if count != 1:
        raise ValueError(f'Unrecognized {table}.{column} schema; migration stopped without dropping data.')
    connection.execute(sql)
    columns = ','.join('"' + r['name'].replace('"', '""') + '"' for r in connection.execute(f'PRAGMA table_info({table})'))
    connection.execute(f'INSERT INTO {temporary}({columns}) SELECT {columns} FROM {table}')
    connection.execute(f'DROP TABLE {table}')
    connection.execute(f'ALTER TABLE {temporary} RENAME TO {table}')
    for statement in extras:
        connection.execute(statement)


def initialize_workflow(connection):
    allowed = ','.join(repr(s) for s in STATUSES)
    templates = ','.join(repr(s) for s in SCOPES)
    connection.execute(f'CREATE TABLE IF NOT EXISTS workflow_statuses(status TEXT PRIMARY KEY CHECK(status IN ({allowed})))')
    connection.executemany('INSERT OR IGNORE INTO workflow_statuses VALUES(?)', [(s,) for s in STATUSES])
    new_scopes = not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='planning_scopes'").fetchone()
    connection.execute(f'''CREATE TABLE IF NOT EXISTS planning_scopes(
        scope TEXT PRIMARY KEY CHECK(length(trim(scope))>0 AND scope=lower(trim(scope))),
        template_scope TEXT NOT NULL CHECK(template_scope IN ({templates})))''')
    if new_scopes:
        connection.executemany('INSERT INTO planning_scopes VALUES(?,?)', [(s,s) for s in SCOPES])
    for table in ('generation_plans', 'generation_plan_steps'):
        _add_reference(connection, table, 'status', 'workflow_statuses', 'status')
    _add_reference(connection, 'generation_plans', 'scope', 'planning_scopes', 'scope')
    columns = {r['name'] for r in connection.execute('PRAGMA table_info(generation_phases)')}
    if 'status' not in columns:
        connection.execute("ALTER TABLE generation_phases ADD COLUMN status TEXT NOT NULL DEFAULT 'pending' REFERENCES workflow_statuses(status) ON DELETE RESTRICT")


def initialize_minute_timestamps(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS _schema_migrations(name TEXT PRIMARY KEY)')
    if connection.execute("SELECT 1 FROM _schema_migrations WHERE name='minute_timestamps'").fetchone():
        return
    for table in ('scenes','ontological_components','generation_phases','generation_plans','generation_plan_revisions','scene_revisions'):
        columns = {r['name'] for r in connection.execute(f'PRAGMA table_info({table})')}
        for column in ('created_at','updated_at'):
            if column not in columns:
                continue
            for row in connection.execute(f'SELECT DISTINCT {column} FROM {table}').fetchall():
                try:
                    value = datetime.fromisoformat(row[0]).isoformat(timespec='minutes')
                except (TypeError,ValueError):
                    continue
                if value != row[0]:
                    connection.execute(f'UPDATE {table} SET {column}=? WHERE {column}=?',(value,row[0]))
    connection.execute("INSERT INTO _schema_migrations VALUES('minute_timestamps')")
