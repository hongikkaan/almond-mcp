import asyncio

import pytest

from offline_rhino import (
    ATTACH, EXECUTE, OBSERVE, RECOVER, OfflineRhino, broker_for, rejected, value,
)
from project import write_json


FIRST_REPLY_SECONDS = 0.25


@pytest.fixture
def execution_root(tmp_path_factory):
    # Leave space for the journal's full identifiers and atomic-write suffix.
    return tmp_path_factory.mktemp("e")


def test_cancel_before_dispatch_keeps_session_usable(execution_root):
    async def scenario():
        target = OfflineRhino(execution_root / "model", "drawing", pid=2999911)
        async with broker_for(execution_root / "host", [target]) as broker:
            connection_id = (await value(broker, ATTACH, **target.attach_args))["connection_id"]
            target.begin_gate = asyncio.Event()
            canceled = asyncio.create_task(broker.call(OBSERVE, {"connection_id": connection_id}))
            await target.begin_received.wait()
            canceled.cancel()
            with pytest.raises(asyncio.CancelledError):
                await canceled

            target.begin_gate.set()
            assert (await value(broker, OBSERVE, connection_id=connection_id))["model"] == "drawing.3dm"
            assert target.worker.calls == [{}]

    asyncio.run(asyncio.wait_for(scenario(), 10))


def test_timeout_recovers_exact_result_and_fences_until_worker_returns(execution_root):
    async def scenario():
        target = OfflineRhino(execution_root / "model", "drawing", pid=2999912)
        data = execution_root / "host"
        async with broker_for(data, [target], call_timeout=FIRST_REPLY_SECONDS) as broker:
            connection_id = (await value(broker, ATTACH, **target.attach_args))["connection_id"]
            binding = target.binding
            target.worker.gate = asyncio.Event()
            initial = await value(broker, EXECUTE, connection_id=connection_id, code="result = 42")
            execution = target.worker.execution
            assert initial["request_id"] == execution.request_id and not initial["completed"]
            args = {"request_id": execution.request_id, "connection_id": connection_id}
            expected = {"answer": 42}
            execution.finish(expected)

            durable = await value(broker, RECOVER, **args)
            assert durable["completed"] and durable["result"] == expected
            await rejected(broker, OBSERVE, connection_id=connection_id)
            await rejected(broker, RECOVER, **{**args, "connection_id": "a" * 32})

            target.worker.gate.set()
            await target.worker.returned.wait()
            observed = await value(broker, RECOVER, **args)
            assert observed["completed"] and observed["result"] == expected
            assert (await value(broker, OBSERVE, connection_id=connection_id))["model"] == "drawing.3dm"

        async with broker_for(data, [target]) as restarted:
            retained = await value(restarted, RECOVER, **args)
            assert retained["result"] == expected and retained["requires_reconnect"]
            await rejected(restarted, RECOVER, **{**args, "connection_id": "b" * 32})
            write_json(
                binding["ready_path"], {**binding, "document_serial": target.serial + 1},
            )
            assert "target changed" in await rejected(restarted, RECOVER, **args)

    asyncio.run(asyncio.wait_for(scenario(), 10))


@pytest.mark.parametrize("evidence", ["missing-manifest", "stale-operation"])
def test_timeout_with_unproven_identity_keeps_session_fenced(execution_root, evidence):
    async def scenario():
        target = OfflineRhino(execution_root / "model", "drawing", pid=2999913)
        async with broker_for(execution_root / "host", [target], call_timeout=FIRST_REPLY_SECONDS) as broker:
            connection_id = (await value(broker, ATTACH, **target.attach_args))["connection_id"]
            target.worker.gate = asyncio.Event()
            target.worker.publish_manifest = evidence != "missing-manifest"
            target.worker.stale_operation = evidence == "stale-operation"
            error = await rejected(broker, EXECUTE, connection_id=connection_id, code="result = 42")
            assert "outcome is unknown" in error
            await rejected(broker, OBSERVE, connection_id=connection_id)
            assert target.worker.calls == []

    asyncio.run(asyncio.wait_for(scenario(), 10))


def test_cancel_after_dispatch_preserves_execution_and_blocks_replay(execution_root):
    async def scenario():
        target = OfflineRhino(execution_root / "model", "drawing", pid=2999914)
        async with broker_for(execution_root / "host", [target]) as broker:
            connection_id = (await value(broker, ATTACH, **target.attach_args))["connection_id"]
            target.worker.gate = asyncio.Event()
            invocation = {"connection_id": connection_id, "code": "change_model()"}
            caller = asyncio.create_task(broker.call(EXECUTE, invocation))
            await target.worker.entered.wait()
            caller.cancel()
            with pytest.raises(asyncio.CancelledError):
                await caller

            execution = target.worker.execution
            execution.finish({"changes": 1})
            target.worker.gate.set()
            await rejected(broker, EXECUTE, **invocation)

            retained = await value(
                broker, RECOVER, connection_id=connection_id, request_id=execution.request_id,
            )
            assert retained["completed"] and retained["result"] == {"changes": 1}
            assert (await value(broker, OBSERVE, connection_id=connection_id))["model"] == "drawing.3dm"

    asyncio.run(asyncio.wait_for(scenario(), 10))
