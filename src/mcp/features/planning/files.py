"""Project file references: readable names, stable keys, private model identity."""
from __future__ import annotations

import ntpath
import uuid


class ProjectFilesStore:
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
