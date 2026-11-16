"""Project file catalog and private model locations keyed by filename."""
from __future__ import annotations

import ntpath
import uuid


def initialize_phase_files(connection):
    """Add ordered Phase/file relations while retaining the legacy first-file key."""
    if 'file_id' not in {r['name'] for r in connection.execute('PRAGMA table_info(project_files)')}:
        connection.execute('''CREATE TABLE IF NOT EXISTS generation_phase_files(
            phase_id TEXT NOT NULL REFERENCES generation_phases(phase_id) ON DELETE CASCADE,
            file_name TEXT NOT NULL REFERENCES project_files(file_name) ON DELETE RESTRICT,
            position INTEGER NOT NULL CHECK(position>=0),
            PRIMARY KEY(phase_id,file_name), UNIQUE(phase_id,position))''')
        connection.execute('''INSERT INTO generation_phase_files(phase_id,file_name,position)
            SELECT phase_id,file_name,0 FROM generation_phases p
            WHERE file_name IS NOT NULL AND NOT EXISTS(
                SELECT 1 FROM generation_phase_files f WHERE f.phase_id=p.phase_id)''')
        return
    connection.execute('''CREATE TABLE IF NOT EXISTS generation_phase_files(
        phase_id TEXT NOT NULL REFERENCES generation_phases(phase_id) ON DELETE CASCADE,
        file_id TEXT NOT NULL REFERENCES project_files(file_id) ON DELETE RESTRICT,
        position INTEGER NOT NULL CHECK(position>=0),
        PRIMARY KEY(phase_id,file_id), UNIQUE(phase_id,position))''')
    connection.execute('''INSERT INTO generation_phase_files(phase_id,file_id,position)
        SELECT phase_id,project_file_id,0 FROM generation_phases p
        WHERE project_file_id IS NOT NULL AND NOT EXISTS(
            SELECT 1 FROM generation_phase_files f WHERE f.phase_id=p.phase_id)''')
    # An older store can still write the singular key. Preserve its intended
    # replacement rather than leaving an unrelated stale plural association.
    connection.execute('''CREATE TRIGGER IF NOT EXISTS phase_file_legacy_insert
        AFTER INSERT ON generation_phases WHEN NEW.project_file_id IS NOT NULL
        BEGIN INSERT INTO generation_phase_files VALUES(NEW.phase_id,NEW.project_file_id,0); END''')
    connection.execute('''CREATE TRIGGER IF NOT EXISTS phase_file_legacy_update
        AFTER UPDATE OF project_file_id ON generation_phases
        WHEN NEW.project_file_id IS NOT OLD.project_file_id
        BEGIN
            DELETE FROM generation_phase_files WHERE phase_id=NEW.phase_id;
            INSERT INTO generation_phase_files SELECT NEW.phase_id,NEW.project_file_id,0
                WHERE NEW.project_file_id IS NOT NULL;
        END''')


class ProjectFilesStore:
    def _phase_file_references(self, connection, file_name):
        if isinstance(file_name, str):
            names = [file_name] if file_name.strip() else []
        elif isinstance(file_name, list) and all(isinstance(n, str) and n.strip() for n in file_name):
            names = file_name
        else:
            raise ValueError('file_name must be a filename string or an array of nonempty filenames.')
        return list(dict.fromkeys(self._project_file_reference(connection, name) for name in names))

    @staticmethod
    def _write_phase_files(connection, phase_id, file_names):
        connection.execute('DELETE FROM generation_phase_files WHERE phase_id=?', (phase_id,))
        connection.executemany('INSERT INTO generation_phase_files VALUES(?,?,?)',
                               [(phase_id, name, i) for i, name in enumerate(file_names)])

    def _legacy_project_file_reference(self, connection, file_name='', *, model_path=''):
        if not isinstance(file_name, str):
            raise ValueError('file_name must be a filename string.')
        file_name = file_name.strip()
        if model_path:
            model_path = self._component_model_path(model_path)
            file_name = ntpath.basename(model_path)
            match = connection.execute('SELECT file_id FROM _project_file_locations WHERE model_path=?', (model_path,)).fetchone()
            if match:
                return match[0]
        if not file_name:
            return None
        if file_name in {'.','..'} or any(c in file_name for c in ('/', chr(92), ':')):
            raise ValueError('file_name must contain only the filename; use project_file_id for an existing file.')
        rows = connection.execute('SELECT file_id FROM project_files WHERE file_name=? COLLATE NOCASE ORDER BY file_id', (file_name,)).fetchall()
        if model_path:
            rows = [r for r in rows if not connection.execute('SELECT 1 FROM _project_file_locations WHERE file_id=?',(r[0],)).fetchone()]
        if len(rows) > 1:
            raise ValueError('Several project files have this name; select a project_file_id.')
        file_id = rows[0][0] if rows else str(uuid.uuid4())
        if not rows:
            connection.execute('INSERT INTO project_files(file_id,file_name) VALUES(?,?)', (file_id,file_name))
        if model_path:
            connection.execute('INSERT INTO _project_file_locations(file_id,model_path) VALUES(?,?)',(file_id,model_path))
        return file_id

    @staticmethod
    def _clean_file_name(file_name):
        if not isinstance(file_name, str):
            raise ValueError('file_name must be a filename string.')
        name = file_name.strip()
        if name in {'.', '..'} or any(c in name for c in ('/', chr(92), ':')):
            raise ValueError('file_name must contain only the filename.')
        return name

    @staticmethod
    def _find_project_file(connection, name):
        # SQLite NOCASE folds ASCII only; use the same Windows casing rule
        # that the migration uses, while storing one canonical display spelling.
        key = ntpath.normcase(name)
        return next((row for row in connection.execute('SELECT file_name,description,registered FROM project_files')
                     if ntpath.normcase(row['file_name']) == key), None)

    def _project_file_reference(self, connection, file_name='', *, model_path=''):
        if model_path:
            model_path = self._component_model_path(model_path)
            name = self._clean_file_name(ntpath.basename(model_path))
        else:
            name = self._clean_file_name(file_name)
            if not name:
                return None
        row = self._find_project_file(connection, name)
        if not model_path:
            if row is None or not row['registered']:
                raise ValueError(f'Project file {name!r} is not registered. Register it before selecting it.')
            return row['file_name']
        if row is None:
            connection.execute('INSERT INTO project_files(file_name,registered) VALUES(?,0)', (name,))
        else:
            name = row['file_name']
        current = connection.execute('SELECT model_path FROM _project_file_locations WHERE file_name=?', (name,)).fetchone()
        if current is None:
            connection.execute('INSERT INTO _project_file_locations(file_name,model_path) VALUES(?,?)', (name, model_path))
        elif ntpath.normcase(current['model_path']) != ntpath.normcase(model_path):
            raise ValueError(f'Project filename {name!r} already identifies {current["model_path"]}; cannot link {model_path}.')
        return name

    def upsert_project_file(self, file_name, description=None):
        name = self._clean_file_name(file_name)
        if not name:
            raise ValueError('file_name must not be empty.')
        if description is not None and not isinstance(description, str):
            raise ValueError('description must be a string or null.')
        with self._connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = self._find_project_file(connection, name)
            if row is None:
                description = description or None
                connection.execute('INSERT INTO project_files(file_name,description,registered) VALUES(?,?,1)', (name,description))
            else:
                name = row['file_name']
                description = row['description'] if description is None else description or None
                connection.execute('UPDATE project_files SET description=?,registered=1 WHERE file_name=?', (description,name))
        return dict(file_name=name, description=description)

    def list_project_files(self, limit=50, offset=0):
        if type(limit) is not int or not 1 <= limit <= 500 or type(offset) is not int or offset < 0:
            raise ValueError('limit must be 1–500 and offset must be nonnegative integers.')
        with self._connect() as connection:
            connection.execute('BEGIN')
            total = connection.execute('SELECT COUNT(*) FROM project_files WHERE registered=1').fetchone()[0]
            files = [dict(row) for row in connection.execute('SELECT file_name,description FROM project_files WHERE registered=1 ORDER BY file_name COLLATE NOCASE,file_name LIMIT ? OFFSET ?', (limit,offset))]
        return dict(files=files,total=total,limit=limit,offset=offset,truncated=offset+len(files)<total)
