"""Controlled workflow vocabulary and migrations that preserve dependent rows."""
from __future__ import annotations

import re
import json
from datetime import datetime

STATUSES = ('pending', 'running', 'completed', 'failed', 'blocked', 'paused')
TASK_SCOPES = ('spatial_development', 'plan_editing', 'construction_detail', 'model_revision', 'inspection')
SCOPES = ('house', 'interior', 'structure', 'drawing', 'component', *TASK_SCOPES)


def default_plan_title(goal: str) -> str:
    """Give legacy records a readable label without changing their full goal."""
    first_line = next((line.strip() for line in goal.splitlines() if line.strip()), "Untitled Plan")
    first_line = ' '.join(first_line.split())
    return first_line if len(first_line) <= 80 else first_line[:79].rstrip() + '…'


def same_kind_ids(values, kind: str) -> list[str]:
    if (not isinstance(values, list) or any(not isinstance(value, str)
            or not value.startswith(kind + '_') or not value[len(kind) + 1:].strip() for value in values)):
        raise ValueError(f"depends_on must contain only {kind}_ IDs.")
    # These describe relationships; existence, cycles and execution are not gates.
    return list(values)


def initialize_planning_details(store, connection):
    """Add labels and retire mixed-kind dependencies and Step target overrides."""
    migration = 'planning_details_v1'
    if connection.execute('SELECT 1 FROM _schema_migrations WHERE name=?', (migration,)).fetchone():
        return
    connection.execute('''CREATE TABLE IF NOT EXISTS _retired_step_targets(
        plan_id TEXT NOT NULL, step_id TEXT NOT NULL, component_ids_json TEXT NOT NULL,
        PRIMARY KEY(plan_id,step_id))''')
    affected = set()
    for row in connection.execute('''SELECT plan_id,step_id FROM generation_plan_steps s
            WHERE component_refs_set=1 OR EXISTS (SELECT 1 FROM generation_step_ontological r
                WHERE r.plan_id=s.plan_id AND r.step_id=s.step_id)''').fetchall():
        ids = [r[0] for r in connection.execute('''SELECT ontological_id FROM generation_step_ontological
            WHERE plan_id=? AND step_id=? ORDER BY position''', (row['plan_id'], row['step_id']))]
        connection.execute('INSERT OR IGNORE INTO _retired_step_targets VALUES(?,?,?)',
                           (row['plan_id'], row['step_id'], json.dumps(ids)))
        affected.add(row['plan_id'])
    connection.execute('DELETE FROM generation_step_ontological')
    connection.execute('UPDATE generation_plan_steps SET component_refs_set=0 WHERE component_refs_set<>0')
    for table, key, kind in (('generation_phases', 'phase_id', 'phase'), ('generation_plans', 'plan_id', 'plan')):
        for row in connection.execute(f'SELECT {key},depends_on_json FROM {table}').fetchall():
            old = json.loads(row['depends_on_json'])
            kept = [v for v in old if isinstance(v, str) and v.startswith(kind + '_') and v[len(kind) + 1:].strip()]
            if old != kept:
                connection.execute(f'UPDATE {table} SET depends_on_json=? WHERE {key}=?',
                                   (json.dumps(kept), row[key]))
                if kind == 'plan':
                    affected.add(row[key])
    for row in connection.execute("SELECT plan_id,goal FROM generation_plans WHERE trim(title)=''").fetchall():
        # Additive schema backfill preserves the original timestamps/revisions.
        # Authored title changes use update_plan and receive a new revision.
        connection.execute('UPDATE generation_plans SET title=? WHERE plan_id=?',
                           (default_plan_title(row['goal']), row['plan_id']))
    for plan_id in sorted(affected):
        store._record_generation_revision(connection, plan_id, migration)
    connection.execute('INSERT INTO _schema_migrations VALUES(?)', (migration,))


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
    else:
        sql = connection.execute("SELECT sql FROM sqlite_master WHERE name='planning_scopes'").fetchone()[0]
        if not all(repr(scope) in sql for scope in TASK_SCOPES):
            if connection.execute('PRAGMA foreign_keys').fetchone()[0]:
                raise RuntimeError('Scope migration requires the initialization transaction.')
            rebuilt, count = re.subn(r'CHECK\s*\(\s*template_scope\s+IN\s*\([^)]*\)\s*\)',
                                    f'CHECK(template_scope IN ({templates}))', sql, count=1, flags=re.I)
            if count != 1:
                raise ValueError('Unrecognized planning_scopes constraint; migration stopped without dropping data.')
            rebuilt = re.sub(r'^(CREATE TABLE\s+)(?:"?planning_scopes"?)',
                             r'\g<1>_migrate_planning_scopes', rebuilt, count=1, flags=re.I)
            extras = [row[0] for row in connection.execute(
                "SELECT sql FROM sqlite_master WHERE tbl_name='planning_scopes' AND type IN ('index','trigger') AND sql IS NOT NULL")]
            connection.execute(rebuilt)
            connection.execute('INSERT INTO _migrate_planning_scopes SELECT * FROM planning_scopes')
            connection.execute('DROP TABLE planning_scopes')
            connection.execute('ALTER TABLE _migrate_planning_scopes RENAME TO planning_scopes')
            for statement in extras:
                connection.execute(statement)
        # Preserve custom scopes, including a pre-existing mapping with a new built-in name.
        connection.executemany('INSERT OR IGNORE INTO planning_scopes VALUES(?,?)', [(s,s) for s in TASK_SCOPES])
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
    for table in ('scenes','ontological_holons','generation_phases','generation_plans','generation_plan_revisions','scene_revisions'):
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
