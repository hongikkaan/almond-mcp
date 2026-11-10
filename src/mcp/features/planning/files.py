"""Project file references: readable names, stable keys, private model identity."""
from __future__ import annotations

import ntpath
import uuid


def initialize_phase_files(connection):
    """Add ordered Phase/file relations while retaining the legacy first-file key."""
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
    def _phase_file_references(self, connection, file_name, project_file_id=None):
        if isinstance(file_name, str):
            names = [file_name] if file_name.strip() else []
        elif isinstance(file_name, list) and all(isinstance(n, str) and n.strip() for n in file_name):
            names = file_name
        else:
            raise ValueError('file_name must be a filename string or an array of nonempty filenames.')
        if project_file_id is not None:
            if len(names) > 1:
                raise ValueError('A legacy project_file_id can select only one file.')
            return [self._project_file_reference(connection, names[0] if names else '', project_file_id)]
        # Resolve the entire request in the caller's transaction. Ambiguous
        # names never select an arbitrary model and a later failure rolls back.
        ids = []
        for name in names:
            try:
                file_id = self._project_file_reference(connection, name)
            except ValueError as exc:
                if 'only the filename' in str(exc):
                    raise ValueError('file_name에는 폴더 경로를 제외한 파일명만 입력합니다.') from exc
                if 'Several project files' in str(exc):
                    raise ValueError(f'File name {name!r} matches several registered files. Give the files distinct names before assigning this Phase.') from exc
                raise
            if file_id not in ids:
                ids.append(file_id)
        return ids

    @staticmethod
    def _write_phase_files(connection, phase_id, file_ids):
        connection.execute('DELETE FROM generation_phase_files WHERE phase_id=?', (phase_id,))
        connection.executemany('INSERT INTO generation_phase_files VALUES(?,?,?)',
                               [(phase_id, file_id, i) for i, file_id in enumerate(file_ids)])

    def _project_file_reference(self, connection, file_name='', project_file_id=None, *, model_path=''):
        if not isinstance(file_name, str):
            raise ValueError('file_name must be a filename string.')
        file_name = file_name.strip()
        if model_path:
            model_path = self._component_model_path(model_path)
            file_name = ntpath.basename(model_path)
            match = connection.execute('SELECT file_id FROM _project_file_locations WHERE model_path=?', (model_path,)).fetchone()
            if match:
                return match[0]
        if project_file_id is not None:
            if not isinstance(project_file_id, str) or not project_file_id:
                raise ValueError('project_file_id must identify an existing project file.')
            row = connection.execute('SELECT file_name FROM project_files WHERE file_id=?', (project_file_id,)).fetchone()
            if row is None:
                raise KeyError(f'Unknown project_file_id: {project_file_id}')
            if file_name and file_name.casefold() != row[0].casefold():
                raise ValueError('file_name and project_file_id identify different files.')
            return project_file_id
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

    def list_project_files(self, limit=50, offset=0):
        if type(limit) is not int or not 1 <= limit <= 500 or type(offset) is not int or offset < 0:
            raise ValueError('limit must be 1–500 and offset must be nonnegative integers.')
        with self._connect() as connection:
            connection.execute('BEGIN')
            total = connection.execute('SELECT COUNT(*) FROM project_files').fetchone()[0]
            files = [dict(row) for row in connection.execute('SELECT file_id AS project_file_id,file_name FROM project_files ORDER BY file_name COLLATE NOCASE,file_id LIMIT ? OFFSET ?', (limit,offset))]
        return dict(files=files,total=total,limit=limit,offset=offset,truncated=offset+len(files)<total)
