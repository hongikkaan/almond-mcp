"""Real Windows leases and disposable DB migration protect shared data."""
from pathlib import Path
from contextlib import closing
import sqlite3

import pytest
from project import ExclusiveFile, SharedStorageLease, connection_paths
from shared_store import StoreGate
from storage_cleanup import migrate_database


def test_two_documents_share_storage_but_not_connection_paths(tmp_path):
    a, b = tmp_path / "a.3dm", tmp_path / "b.3dm"
    a.touch()
    b.touch()
    one = connection_paths(a, "A", "a" * 32, create=True)
    two = connection_paths(b, "B", "b" * 32, create=True)
    assert one["state_db"] == two["state_db"]
    assert one["session_dir"] != two["session_dir"]
    assert one["call_root"] != two["call_root"]


def test_leases_exclude_old_owner_and_simultaneous_db_writer(tmp_path):
    (tmp_path / ".sessions").mkdir()
    with SharedStorageLease(tmp_path), SharedStorageLease(tmp_path):
        with pytest.raises(OSError):
            ExclusiveFile(tmp_path / "mcp.lock")
        with StoreGate(tmp_path):
            with pytest.raises(TimeoutError):
                with StoreGate(tmp_path, timeout=0):
                    pass
    with ExclusiveFile(tmp_path / "mcp.lock"), StoreGate(tmp_path, timeout=0):
        pass


def test_legacy_db_migration_preserves_data_and_refuses_conflict(tmp_path):
    (tmp_path / ".sessions").mkdir()
    legacy, target = tmp_path / "DB", tmp_path / "scene.sqlite3"
    with closing(sqlite3.connect(legacy)) as db:
        db.execute("CREATE TABLE evidence(value TEXT)")
        db.execute("INSERT INTO evidence VALUES ('original')")
        db.commit()
    assert migrate_database({"storage": str(tmp_path)}, "a" * 32)
    assert not legacy.exists()
    with closing(sqlite3.connect(target)) as db:
        assert db.execute("SELECT value FROM evidence").fetchone() == ("original",)
    legacy.write_bytes(b"old")
    before = target.read_bytes()
    with pytest.raises(RuntimeError, match="Both scene.sqlite3 and DB exist"):
        migrate_database({"storage": str(tmp_path)}, "a" * 32)
    assert legacy.read_bytes() == b"old" and target.read_bytes() == before
