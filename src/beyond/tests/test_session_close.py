"""Retained close requests require their original connection."""
import asyncio
from types import SimpleNamespace

import pytest

from project import ExclusiveFile
from session_close import SessionCloser


@pytest.mark.parametrize("lock_held", [False, True])
def test_retained_close_requires_original_explicit_connection(tmp_path, lock_held):
    closer = SessionCloser(tmp_path)
    request = "close-one"
    closer.persist(dict(schema="almond-session-close", version=1, request_id=request,
                        connection_id="connection-a", status="completed", stage="completed"))
    restarted = SessionCloser(tmp_path)
    broker = SimpleNamespace(connections={})
    lock = ExclusiveFile(closer.directory(request) / "request.lock") if lock_held else None
    try:
        with pytest.raises(RuntimeError, match="another connection"):
            asyncio.run(restarted.run(broker, "connection-b", request_id=request))
        with pytest.raises(ValueError, match="connection_id"):
            asyncio.run(restarted.run(broker, None, request_id=request))
        recovered = asyncio.run(restarted.run(broker, "connection-a", request_id=request))
        assert recovered["status"] == "completed"
    finally:
        if lock is not None:
            lock.close()
