"""CLI routes keep their contracts when importing canonical feature modules."""
import json
import os
import subprocess
import sys

from almond_mcp import cli
from almond_mcp.features.assets import asset_repository


def run_cli(tmp_path, *arguments, input_bytes=None):
    environment = dict(os.environ, ALMOND_DESIGN_CODE_DIR=str(tmp_path / "design-codes"))
    return subprocess.run(
        [sys.executable, "-B", "-X", "utf8", "-m", "almond_mcp.cli", *arguments],
        input=input_bytes, capture_output=True, env=environment, timeout=30, check=True,
    )


def test_design_code_cli_lists_builtin_profiles_from_canonical_module(tmp_path):
    result = run_cli(tmp_path, "design-codes", "--json")
    listing = json.loads(result.stdout)
    assert listing["default"] == "eurocode"
    assert "eurocode" in {profile["id"] for profile in listing["profiles"]}
    assert listing["problems"] == []


def test_solve_cli_accepts_bom_encoded_json_and_returns_protocol_reply(tmp_path):
    result = run_cli(tmp_path, "solve", input_bytes=b'\xef\xbb\xbf{"ping":true}')
    reply = json.loads(result.stdout)
    assert reply["status"] == "ok"
    assert reply["protocol"] == 1
    assert reply["design_codes"]["default"] == "eurocode"


def test_library_cli_dispatches_to_canonical_repository_without_starting_server(monkeypatch):
    calls = []
    monkeypatch.setattr(asset_repository, "serve_library", lambda *args: calls.append(args) or 0)
    assert cli.main(["library", "--port", "8812", "--open"]) == 0
    assert calls == [(8812, True)]
