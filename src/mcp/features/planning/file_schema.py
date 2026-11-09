"""Replace legacy project file IDs without conflating separate Rhino documents."""
import ntpath


def check_file_name_collisions(connection):
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(project_files)")}
    legacy_keys = "file_id" in columns
    files = {}
    if legacy_keys:
        has_locations = connection.execute("SELECT 1 FROM sqlite_master WHERE name='_project_file_locations'").fetchone()
        location = "l.model_path" if has_locations else "NULL AS model_path"
        join = "LEFT JOIN _project_file_locations l ON l.file_id=f.file_id" if has_locations else ""
        for row in connection.execute(f"SELECT f.file_name,{location} FROM project_files f {join} ORDER BY f.file_name,f.file_id"):
            files.setdefault(ntpath.normcase(row["file_name"]), []).append((row["file_name"], row["model_path"]))
    # The oldest registry acquires file records from its saved model paths
    # during migration. Detect those collisions in the read-only preflight too.
    component_columns = {r["name"] for r in connection.execute("PRAGMA table_info(components)")}
    if (legacy_keys or not columns) and "model_path" in component_columns:
        for row in connection.execute("SELECT DISTINCT model_path FROM components WHERE model_path IS NOT NULL ORDER BY model_path"):
            path = row[0]
            name = ntpath.basename(path)
            entries = files.setdefault(ntpath.normcase(name), [])
            key = ntpath.normcase(ntpath.normpath(path))
            if any(bound and ntpath.normcase(ntpath.normpath(bound)) == key for _, bound in entries):
                continue
            unnamed = next((i for i, (_, bound) in enumerate(entries) if not bound), None)
            if unnamed is None:
                entries.append((name, path))
            else:
                entries[unnamed] = (entries[unnamed][0], path)
    collisions = [rows for rows in files.values() if len(rows) > 1]
    if collisions:
        evidence = "; ".join(", ".join(
            f"{name} ({path or 'path unknown'})" for name, path in rows
        ) for rows in collisions)
        raise ValueError(f"Project file migration requires unique filenames. Conflicting records: {evidence}")
    return legacy_keys


def migrate_project_file_keys(connection):
    if not check_file_name_collisions(connection):
        return
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(project_files)")}
    description = "description" if "description" in columns else "NULL"
    for view in ("_scene_records", "_phase_records", "_component_records"):
        connection.execute(f"DROP VIEW IF EXISTS {view}")
    for trigger in ("phase_file_legacy_insert", "phase_file_legacy_update"):
        connection.execute(f"DROP TRIGGER IF EXISTS {trigger}")

    for table in ("scenes", "generation_phases"):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN file_name TEXT REFERENCES project_files(file_name) ON DELETE RESTRICT")
        connection.execute(f"""UPDATE {table} SET file_name=(
            SELECT file_name FROM project_files f WHERE f.file_id={table}.project_file_id)""")
        if connection.execute(f"SELECT 1 FROM {table} WHERE project_file_id IS NOT NULL AND file_name IS NULL LIMIT 1").fetchone():
            raise ValueError(f"An unrecognized project file in {table} prevents a lossless migration.")
        connection.execute(f"ALTER TABLE {table} DROP COLUMN project_file_id")

    _replace(connection, "project_files", """
        file_name TEXT PRIMARY KEY NOT NULL COLLATE NOCASE CHECK(length(trim(file_name))>0 AND file_name NOT IN ('.','..')
            AND instr(file_name,'/')=0 AND instr(file_name,char(92))=0 AND instr(file_name,':')=0),
        description TEXT,
        registered INTEGER NOT NULL CHECK(registered IN (0,1))
    """, f"SELECT file_name,{description},1 FROM project_files", before_drop=lambda: _copy_relations(connection))
    initialize_file_views(connection)


def _replace(connection, name, definition, select, *, before_drop=None):
    expected = connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    connection.execute(f"CREATE TABLE _new{name}({definition})")
    copied = connection.execute(f"INSERT INTO _new{name} {select}").rowcount
    if copied != expected:
        raise ValueError(f"Missing project file references in {name} prevent a lossless migration.")
    if before_drop is not None:
        before_drop()
    connection.execute(f"DROP TABLE {name}")
    connection.execute(f"ALTER TABLE _new{name} RENAME TO {name}")


def _copy_relations(connection):
    _replace(connection, "_project_file_locations", """
        file_name TEXT PRIMARY KEY NOT NULL REFERENCES project_files(file_name) ON DELETE RESTRICT,
        model_path TEXT NOT NULL UNIQUE
    """, """SELECT f.file_name,l.model_path FROM _project_file_locations l JOIN project_files f ON f.file_id=l.file_id""")
    _replace(connection, "generation_phase_files", """
        phase_id TEXT NOT NULL REFERENCES generation_phases(phase_id) ON DELETE CASCADE,
        file_name TEXT NOT NULL REFERENCES project_files(file_name) ON DELETE RESTRICT,
        position INTEGER NOT NULL CHECK(position>=0),
        PRIMARY KEY(phase_id,file_name), UNIQUE(phase_id,position)
    """, """SELECT r.phase_id,f.file_name,r.position FROM generation_phase_files r JOIN project_files f ON f.file_id=r.file_id""")
    _replace(connection, "scene_object_membership", """
        scene_id TEXT NOT NULL REFERENCES scenes(scene_id) ON DELETE CASCADE,
        file_name TEXT NOT NULL REFERENCES project_files(file_name) ON DELETE RESTRICT,
        rhino_guid TEXT NOT NULL, included INTEGER NOT NULL CHECK(included IN (0,1)),
        PRIMARY KEY(scene_id,file_name,rhino_guid)
    """, """SELECT s.scene_id,f.file_name,s.rhino_guid,s.included FROM scene_object_membership s
        JOIN project_files f ON f.file_id=s.project_file_id""")
    _replace(connection, "ontological_holons", """
        ontological_id TEXT PRIMARY KEY,
        file_name TEXT NOT NULL REFERENCES project_files(file_name) ON DELETE RESTRICT,
        rhino_group_id TEXT NOT NULL,name TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
        parent_ontological_id TEXT REFERENCES ontological_holons(ontological_id) ON DELETE RESTRICT,
        availability TEXT NOT NULL DEFAULT 'present' CHECK(availability IN ('present','missing_group','unregistered')),
        geometry_digest TEXT NOT NULL DEFAULT '',
        object_count INTEGER NOT NULL DEFAULT 0,effective_object_count INTEGER NOT NULL DEFAULT 0,
        effective_summary_stale INTEGER NOT NULL DEFAULT 0 CHECK(effective_summary_stale IN (0,1)),
        object_types_json TEXT NOT NULL DEFAULT '{}',bounds_json TEXT NOT NULL DEFAULT 'null',
        UNIQUE(file_name,rhino_group_id)
    """, """SELECT c.ontological_id,f.file_name,c.rhino_group_id,c.name,c.created_at,c.updated_at,
        c.parent_ontological_id,c.availability,c.geometry_digest,c.object_count,c.effective_object_count,
        c.effective_summary_stale,c.object_types_json,c.bounds_json
        FROM ontological_holons c JOIN project_files f ON f.file_id=c.project_file_id""")


def initialize_file_views(connection):
    for table, view in (("scenes", "_scene_records"), ("generation_phases", "_phase_records")):
        connection.execute(f"CREATE VIEW IF NOT EXISTS {view} AS SELECT * FROM {table}")
    for view in ('_component_records', '_scene_component_refs', '_plan_component_refs', '_step_component_refs'):
        connection.execute(f'DROP VIEW IF EXISTS {view}')
    from almond_mcp.features.components.semantic_schema import initialize_parent_guards
    initialize_parent_guards(connection, "file_name")
