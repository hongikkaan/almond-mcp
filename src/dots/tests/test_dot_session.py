import json
import os
from pathlib import Path
import subprocess
import sys

from stdio_peer import ATTACH, INSPECT, PIXEL


TESTS = Path(__file__).resolve().parent


def _call(request_id, name, **arguments):
    return {"id": request_id, "op": "call", "name": name, "arguments": arguments}


def _run_dot(scratch, requests, call_timeout=10):
    log = scratch / "received.jsonl"
    lines = [value if isinstance(value, str) else json.dumps(value) for value in requests]
    execution = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", str(TESTS.parent / "dot_client.py"),
         "--server-python", sys.executable, "--server-entry", str(TESTS / "stdio_peer.py"),
         "--timeout", str(call_timeout)],
        input="\n".join(lines) + "\n", encoding="utf-8", capture_output=True,
        env=dict(os.environ, DOT_FIXTURE_CALLS=str(log)), timeout=30,
    )
    assert execution.returncode == 0, execution.stdout + execution.stderr
    replies = [json.loads(line) for line in execution.stdout.splitlines()]
    received = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    return replies, received


def test_dot_uses_one_session_and_preserves_connection_choice_and_wire_results(tmp_path):
    replies, received = _run_dot(tmp_path, [
        {"id": "schema", "op": "describe", "names": [INSPECT]},
        _call("attach", ATTACH, model_path="lobby"),
        _call("failed_attach", ATTACH, model_path="unavailable"),
        _call("missing", INSPECT),
        _call("explicit", INSPECT, connection_id="courtyard"),
        "{malformed",
        _call("selected", INSPECT, connection_id="$connection_id"),
        {"op": "shutdown"},
    ])

    assert replies[0]["event"] == "ready"
    assert replies[0]["catalog"]["names"] == [ATTACH, INSPECT]
    assert replies[-1] == {"event": "closed"}
    by_id = {reply["id"]: reply for reply in replies[1:-1]}
    assert by_id["schema"]["tools"][0]["inputSchema"]["required"] == ["connection_id"]
    assert by_id["failed_attach"]["tool_result"]["isError"] is True
    assert by_id["missing"]["tool_result"]["content"][0]["text"] == "connection_id가 지정되지 않았습니다"
    assert by_id["explicit"]["tool_result"]["structuredContent"] == {"document": "courtyard"}
    assert by_id[None]["ok"] is False
    selected = by_id["selected"]["tool_result"]
    assert selected["isError"] is False
    assert selected["structuredContent"] == {"document": "lobby"}
    assert selected["content"] == [{"type": "image", "mimeType": "image/gif", "data": PIXEL}]
    assert received[-3:] == [
        [INSPECT, {}], [INSPECT, {"connection_id": "courtyard"}], [INSPECT, {"connection_id": "lobby"}],
    ]


def test_dot_does_not_repeat_a_call_with_an_unknown_outcome(tmp_path):
    replies, received = _run_dot(tmp_path, [
        _call("timed", INSPECT, connection_id="lobby", stall=True),
        {"id": "still_ready", "op": "catalog"},
        {"op": "shutdown"},
    ], call_timeout=2)
    _, timed, catalog, closed = replies
    assert timed["id"] == "timed" and timed["ok"] is False
    assert catalog["id"] == "still_ready" and catalog["ok"] is True
    assert closed == {"event": "closed"}
    assert received == [[INSPECT, {"connection_id": "lobby", "stall": True}]]
