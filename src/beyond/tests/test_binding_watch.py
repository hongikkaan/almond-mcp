import asyncio
import sys

import pytest

import binding_watch
from binding_watch import BindingWatcher


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows directory notifications")


def test_notifies_only_ready_file_changes(tmp_path):
    async def scenario():
        changes = asyncio.Queue()
        watcher = BindingWatcher(lambda key, error: changes.put_nowait((key, error)))
        ready = tmp_path / "ready.json"
        native = tmp_path / "native.json"
        replacement = tmp_path / "publish.tmp"

        async def expect_ready():
            assert await asyncio.wait_for(changes.get(), 3) == ("session", None)

        try:
            await watcher.add("session", {"session_dir": str(tmp_path), "ready_path": str(ready)})
            for path in (tmp_path / "operation.json", native):
                path.write_text("initial", encoding="utf-8")
                replacement.write_text("replacement", encoding="utf-8")
                replacement.replace(path)
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(changes.get(), 0.25)

            ready.write_text("initial", encoding="utf-8")
            await expect_ready()
            replacement.write_text("replacement", encoding="utf-8")
            replacement.replace(ready)
            await expect_ready()
            ready.unlink()
            await expect_ready()
        finally:
            watcher.remove("session")
            await watcher.close()

    asyncio.run(scenario())


def test_overflow_rechecks_and_rearms(tmp_path, monkeypatch):
    # One short record fits. A long name forces loss in the real Win32 buffer.
    monkeypatch.setattr(binding_watch, "_BUFFER_SIZE", 64)

    async def scenario():
        changes = asyncio.Queue()
        watcher = BindingWatcher(lambda key, error: changes.put_nowait((key, error)))
        ready = tmp_path / "ready.json"
        try:
            await watcher.add("session", {"session_dir": str(tmp_path), "ready_path": str(ready)})
            (tmp_path / ("a" * 100)).touch()
            assert await asyncio.wait_for(changes.get(), 3) == ("session", None)
            (tmp_path / "unrelated").touch()
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(changes.get(), 0.25)
            ready.touch()
            assert await asyncio.wait_for(changes.get(), 3) == ("session", None)
        finally:
            await watcher.close()

    asyncio.run(scenario())


def test_canceled_add_releases_registration(tmp_path):
    async def scenario():
        changes = asyncio.Queue()
        watcher = BindingWatcher(lambda key, error: changes.put_nowait((key, error)))
        ready = tmp_path / "ready.json"
        binding = {"session_dir": str(tmp_path), "ready_path": str(ready)}
        try:
            pending = asyncio.create_task(watcher.add("session", binding))
            await asyncio.sleep(0)
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            await watcher.add("session", binding)
            ready.touch()
            assert await asyncio.wait_for(changes.get(), 3) == ("session", None)
        finally:
            await watcher.close()

    asyncio.run(scenario())
