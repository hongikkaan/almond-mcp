"""Server binding and helper overrides must remain isolated across calls."""
import asyncio

import pytest

from almond_mcp.feature_context import FeatureContext


def test_current_binding_is_read_from_its_own_server():
    first = {"retrieval_store": object(), "_send_and_receive": lambda: "before"}
    second = {"retrieval_store": object(), "_send_and_receive": lambda: "other"}
    a, b = FeatureContext(first), FeatureContext(second)
    assert a.retrieval_store is not b.retrieval_store
    first["_send_and_receive"] = lambda: "after"
    assert a._send_and_receive() == "after"
    assert b._send_and_receive() == "other"
    a.set_state("overlay", "native")
    assert first["overlay"] == "native"
    assert "overlay" not in second
    with pytest.raises(AttributeError):
        a.missing_service


def test_nested_override_restores_after_error():
    context = FeatureContext({"sender": "base", "tempfile": "original"})
    with context.override(sender="outer"):
        with pytest.raises(RuntimeError):
            with context.override(sender="inner", tempfile="call-folder"):
                assert context.sender == "inner"
                assert context.tempfile == "call-folder"
                raise RuntimeError("native helper failed")
        assert context.sender == "outer"
        assert context.tempfile == "original"
    assert context.sender == "base"


def test_async_helper_overrides_do_not_leak():
    context = FeatureContext({"sender": "base"})

    async def operation(value):
        with context.override(sender=value):
            await asyncio.sleep(0)
            return context.sender

    async def run():
        return await asyncio.gather(operation("first"), operation("second"))

    assert asyncio.run(run()) == ["first", "second"]
    assert context.sender == "base"
