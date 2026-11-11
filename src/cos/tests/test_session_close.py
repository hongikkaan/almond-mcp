"""The public close tool saves before exit and never replays a request."""
import asyncio
from types import SimpleNamespace

from external_host import Broker, Connection, json_result


CATALOG = {"tools": []}


def test_close_saves_then_exits_and_repeated_id_only_reads(tmp_path):
    async def run():
        actions = []
        binding = dict(pid=123, process_start_ticks="456", document_serial="7",
                       model_path=str(tmp_path / "model.3dm"), token="a" * 32,
                       session_dir=str(tmp_path / "session"))
        (tmp_path / "model.3dm").write_bytes(b"existing model")
        async def request(action, **_):
            actions.append(action)
            return dict(binding, saved=True, modified=actions.count("save") == 0,
                        read_only=False, state="connected")
        async def close():
            actions.append("worker_closed")
        async def state():
            return dict(pending=False, uncertain=False)
        broker = Broker(CATALOG, data=tmp_path, contract_check=lambda _: None)
        conn = Connection("connection", "host", SimpleNamespace(request=request, close=close),
                          binding["token"], binding=binding,
                          worker=SimpleNamespace(close=close, state=state), state="ready",
                          lease=SimpleNamespace(close=lambda: actions.append("lease_closed")))
        broker.connections[conn.connection_id] = conn
        broker.host_connections[conn.host_id] = conn.connection_id
        broker.selected_connection_id = conn.connection_id
        async def invoke(conn, name, arguments, invocation):
            assert arguments["language"] == "command" and arguments["script"] == "_Save"
            actions.append("save")
            return json_result(dict(completed=True, status="success", request_id="save-request",
                                    result=dict(command_accepted=True, last_command_result=0)))
        broker._invoke_locked = invoke
        class Exit:
            def prepare(self, record, directory):
                actions.append("prepare")
            def launch(self, record, directory):
                assert "lease_closed" not in actions and "worker_closed" not in actions
                actions.append("exit")
            def inspect(self, record, directory):
                return dict(guard_state="exit_dispatched", rhino_closed=True, cli_closed=True)
        broker.session_closer.exit_factory = Exit
        result = await broker.call("close_session", {"request_id": "close-test"})
        assert not result.is_error
        value = result.structured_content
        assert value["status"] == "completed" and value["saved"]
        assert value["rhino_closed"] and value["worker_closed"] and value["released"]
        assert actions.index("save") < actions.index("exit") < actions.index("worker_closed") < actions.index("lease_closed")
        before = list(actions)
        again = await broker.call("close_session", {"request_id": "close-test"})
        assert again.structured_content == value
        assert actions == before and not broker.connections
    asyncio.run(run())
