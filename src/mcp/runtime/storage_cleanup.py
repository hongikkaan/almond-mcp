"""Owned connection scratch and legacy DB migration; independent of work status."""
from contextlib import ExitStack, closing
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import re
import shutil
import sqlite3
import time

from project import ExclusiveFile, read_json


def process_identity_alive(record: dict) -> bool | None:
    """False proves exit/PID reuse; inaccessible identities remain unknown."""
    try:
        pid = int(record["pid"])
        expected = str(record["process_start_ticks"])
    except (KeyError, ValueError, TypeError):
        return None
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False if ctypes.get_last_error() == 87 else None
    try:
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
            return None
        if code.value != 259:
            return False
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
            return None
        ticks = ((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime) + 504911232000000000
        return str(ticks) == expected
    finally:
        kernel.CloseHandle(handle)


def plain_descendant(path: Path, root: Path) -> Path:
    """Check the absolute deletion/move target and every existing ancestor."""
    root, path = root.absolute(), path.absolute()
    if path == root or not path.is_relative_to(root):
        raise ValueError("The owned path must be strictly inside its storage root.")
    for current in (path, *path.parents):
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise ValueError("Owned storage cannot contain filesystem links.")
        if current == root:
            break
    if path.resolve() != path:
        raise ValueError("Owned storage path did not resolve to the expected absolute target.")
    return path


def remove_owned_tree(path: Path, root: Path) -> None:
    path = plain_descendant(path, root)
    if not path.exists():
        return
    # Never traverse a link introduced by a script while cleaning its scratch.
    for parent, directories, files in os.walk(path, followlinks=False):
        for name in directories + files:
            plain_descendant(Path(parent) / name, root)
    shutil.rmtree(path)
    parent = path.parent
    while parent != root:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def migrate_database(locations: dict, own_token: str) -> bool:
    """Call under StoreGate before importing the server or opening its store."""
    storage = Path(locations["storage"])
    old, target = storage / "scene.sqlite3", storage / "DB"
    if not old.exists():
        return False
    plain_descendant(old, storage)
    plain_descendant(target, storage)
    if target.exists():
        raise RuntimeError("Both scene.sqlite3 and DB exist. Neither database was changed; resolve the conflict before starting.")
    for suffix in ("-wal", "-shm", "-journal"):
        plain_descendant(storage / (old.name + suffix), storage)
        destination = plain_descendant(storage / (target.name + suffix), storage)
        if destination.exists():
            raise RuntimeError("DB sidecar files already exist. Neither database was changed; resolve the conflict before starting.")
    for folder in (storage / ".sessions").iterdir():
        if not folder.is_dir() or folder.name == own_token:
            continue
        worker = folder / "worker.json"
        if worker.exists():
            record = read_json(worker)
            if not record.get("closed") and process_identity_alive(record) is not False:
                raise RuntimeError("Another worker may still use scene.sqlite3. Stop that worker before the DB filename migration.")
    with closing(sqlite3.connect(old, timeout=0)) as connection:
        checkpoint = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if checkpoint and checkpoint[0] != 0:
            raise RuntimeError("The old DB is busy; filename migration was not performed.")
        connection.execute("BEGIN EXCLUSIVE")
        connection.commit()
    # Windows rename refuses replacing an existing destination. No data copy and
    # no per-session backup database are created.
    old.rename(target)
    return True


def cleanup_retired_sessions(storage: Path, *, exclude_token: str = "") -> list[str]:
    """Reap retired token metadata only; never inspect Plans or Steps."""
    sessions = storage / ".sessions"
    if not sessions.is_dir():
        return []
    removed = []
    allowed = {"ready.json", "launch.json", "worker.json", "native.json", "operation.json",
               "last-error.json", "launcher.lock", "rhino.lock", "mcp.lock", "work.json", "artifact-write.json"}
    for folder in list(sessions.iterdir()):
        if not re.fullmatch(r"[0-9a-f]{32}", folder.name) or folder.name == exclude_token:
            continue
        try:
            plain_descendant(folder, sessions)
            children = list(folder.iterdir())
            def owned_metadata(child):
                if child.name in allowed:
                    return True
                match = re.fullmatch(r"(.+)\.new-[0-9a-f]{32}", child.name)
                return bool(match and match[1] in allowed)
            if any(child.is_dir() or not owned_metadata(child) for child in children):
                continue
            records = {p.stem: read_json(p) for p in children if p.suffix == ".json"}
            ready, native = records.get("ready", {}), records.get("native", {})
            retired = ready.get("valid") is False or native.get("phase") in {"stopped", "faulted"}
            rhino_gone = process_identity_alive(ready) is False if ready else False
            if not retired and not rhino_gone:
                # A creation crash can leave only lock files; allow a day before
                # reclaiming an unpublished generation, after exclusive probes.
                if ready or native or time.time() - folder.stat().st_mtime < 86400:
                    continue
            worker = records.get("worker")
            if worker and not worker.get("closed") and process_identity_alive(worker) is not False:
                continue
            launch = records.get("launch")
            # launch.json records the Rhino identity for internal/external hosts,
            # not the lifetime of an authored Plan. A stopped connection does not
            # require that unrelated documents in that Rhino process be closed.
            if launch and not retired and process_identity_alive(launch) is not False:
                continue
            if native.get("pending", 0) and not rhino_gone:
                continue
            with ExitStack() as held:
                for name in ("launcher.lock", "rhino.lock", "mcp.lock"):
                    if (folder / name).exists():
                        held.enter_context(ExclusiveFile(folder / name))
            # Tokens cannot be reopened after retirement. All owners/leases were
            # checked; an active or uncertain native owner never reaches here.
            for kind in ("python", "calls"):
                remove_owned_tree(storage / "tmp" / kind / folder.name, storage / "tmp")
            remove_owned_tree(folder, sessions)
            removed.append(folder.name)
        except (OSError, ValueError, RuntimeError):
            continue  # Inaccessible/unknown ownership is retained, never guessed.
    return removed


if __name__ == "__main__":
    import argparse
    from shared_store import StoreGate
    parser = argparse.ArgumentParser(description="Reap retired Almond connection metadata after owners release their leases.")
    parser.add_argument("--storage", type=Path, required=True)
    storage = parser.parse_args().storage.resolve(strict=True)
    if storage.name != ".almond":
        parser.error("storage must be the project's .almond directory")
    with StoreGate(str(storage)):
        cleanup_retired_sessions(storage)
