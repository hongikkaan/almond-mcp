"""Focused offline storage/rename/lease tests; fixtures never contain user models."""
import json
import hashlib
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import closing

from project import project_paths, ExclusiveFile, read_binding


class ProjectTests(unittest.TestCase):
    def setUp(self):
        data = Path(__file__).resolve().parent / 'data'
        data.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='_storage_test_', dir=data)
        self.root = Path(self.temp.name)
        self.model = self.root / '설계 초안.3dm'
        self.model.write_bytes(b'PATH TEST ONLY, NOT A REAL RHINO MODEL')

    def tearDown(self):
        self.temp.cleanup()

    def binding(self, paths, slot='A', token='current'):
        binding = dict(schema='almond-project', label=slot, port=5501+'ABCDEFGHIJ'.index(slot),
                       token=token, pid=os.getpid(), model_path=paths['model_path'])
        ready = Path(paths['storage']) / 'ready.json'
        ready.write_text(json.dumps(binding), encoding='utf-8')
        return ready

    def test_filename_layout(self):
        p = project_paths(self.model, create=True)
        self.assertEqual(Path(p['storage']), self.root / '.almond')
        self.assertEqual(Path(p['state_db']), Path(p['storage'])/'DB')
        self.assertFalse(Path(p['temp']).exists())

    def test_distinct_models_same_folder(self):
        other = self.root / '다른 모델.3dm'
        other.write_bytes(b'x')
        self.assertEqual(project_paths(self.model)['state_db'], project_paths(other)['state_db'])

    def test_switch_slot_keeps_database_path(self):
        p = project_paths(self.model, create=True)
        for slot in 'ABCDEFGHIJ':
            ready = self.binding(p, slot)
            _, loaded = read_binding(ready, 'current')
            self.assertEqual(loaded['state_db'], p['state_db'])

    def test_rename_model_and_storage_keeps_read_write(self):
        p = project_paths(self.model, create=True)
        with closing(sqlite3.connect(p['state_db'])) as db:
            db.execute('CREATE TABLE marker (value TEXT)')
            db.execute('INSERT INTO marker VALUES (?)', ('before rename',))
            db.commit()
        self.binding(p)
        renamed = self.model.with_name('최종 안.3dm')
        self.model.rename(renamed)
        storage = self.root/'.almond'
        new = project_paths(renamed, create=True)
        self.binding(new, 'D', 'after-rename')  # Same as a new launcher writing current metadata.
        _, loaded = read_binding(storage/'ready.json', 'after-rename')
        with closing(sqlite3.connect(loaded['state_db'])) as db:
            self.assertEqual(db.execute('SELECT value FROM marker').fetchone()[0], 'before rename')
            db.execute('INSERT INTO marker VALUES (?)', ('after rename',))
            db.commit()
        with closing(sqlite3.connect(new['state_db'])) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM marker').fetchone()[0], 2)

    def test_rename_and_move_project_keeps_db_temp_and_new_binding(self):
        p = project_paths(self.model, create=True)
        with closing(sqlite3.connect(p['state_db'])) as db:
            db.execute('CREATE TABLE marker (value TEXT)')
            db.execute('INSERT INTO marker VALUES (?)', ('before move',))
            db.commit()
        before = hashlib.sha256(Path(p['state_db']).read_bytes()).hexdigest()
        Path(p['temp']).mkdir()
        (Path(p['temp'])/'review.txt').write_text('keep this artifact', encoding='utf-8')
        self.binding(p)
        renamed = self.root/'이름 변경.3dm'
        self.model.rename(renamed)
        destination = self.root/'다른 위치'/'프로젝트'
        destination.mkdir(parents=True)
        moved_model = renamed.rename(destination/renamed.name)
        (self.root/'.almond').rename(destination/'.almond')
        current = project_paths(moved_model, create=True)
        ready = Path(current['storage'])/'ready.json'
        with self.assertRaises(FileNotFoundError):
            read_binding(ready, 'current')  # Old connection paths are not silently adopted.
        self.binding(current, 'J', 'after-move')  # A fresh launch replaces only metadata.
        binding, loaded = read_binding(ready, 'after-move')
        self.assertEqual(binding['port'], 5510)
        self.assertEqual(loaded['project_dir'], str(destination))
        self.assertEqual(hashlib.sha256(Path(loaded['state_db']).read_bytes()).hexdigest(), before)
        self.assertEqual((Path(loaded['temp'])/'review.txt').read_text(encoding='utf-8'), 'keep this artifact')
        with closing(sqlite3.connect(loaded['state_db'])) as db:
            self.assertEqual(db.execute('SELECT value FROM marker').fetchone()[0], 'before move')
            db.execute('INSERT INTO marker VALUES (?)', ('after move',))
            db.commit()
        with closing(sqlite3.connect(loaded['state_db'])) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM marker').fetchone()[0], 2)

    def test_eleventh_slot_rejected(self):
        p = project_paths(self.model, create=True)
        ready = self.binding(p, 'J')
        b = json.loads(ready.read_text()); b.update(label='K', port=5511)
        ready.write_text(json.dumps(b))
        with self.assertRaises(RuntimeError): read_binding(ready, 'current')

    def test_missing_model_rejected(self):
        with self.assertRaises(FileNotFoundError): project_paths(self.root/'missing.3dm')

    def test_non_model_rejected(self):
        path=self.root/'file.txt'; path.write_text('x')
        with self.assertRaises(ValueError): project_paths(path)

    def test_storage_file_conflict_rejected(self):
        (self.root/'.almond').write_text('not a folder')
        with self.assertRaises(ValueError): project_paths(self.model, create=True)

    def test_wrong_token_rejected(self):
        p=project_paths(self.model, create=True)
        with self.assertRaises(RuntimeError): read_binding(self.binding(p), 'stale')

    def test_invalidated_panel_binding_rejected(self):
        p=project_paths(self.model, create=True); ready=self.binding(p)
        b=json.loads(ready.read_text()); b['valid']=False; ready.write_text(json.dumps(b))
        with self.assertRaises(RuntimeError): read_binding(ready, 'current')

    def test_wrong_port_rejected(self):
        p=project_paths(self.model, create=True); ready=self.binding(p)
        b=json.loads(ready.read_text()); b['port']=5505; ready.write_text(json.dumps(b))
        with self.assertRaises(RuntimeError): read_binding(ready, 'current')

    def test_live_lease_excludes_another_open(self):
        path=self.root/'writer.lock'
        with ExclusiveFile(path):
            with self.assertRaises(OSError): ExclusiveFile(path)
        with ExclusiveFile(path): pass

    def test_stale_lock_file_does_not_block(self):
        path=self.root/'writer.lock'; path.write_text('stale')
        with ExclusiveFile(path): pass


if __name__ == '__main__':
    unittest.main()
