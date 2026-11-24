"""Generated Codex registration and explicit migration, using only fixture files."""
import sys
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from client_config import codex_toml, install_codex, settings


@pytest.mark.parametrize("old_name,old_host", [("rhino", "codex_host.py"), ("almond_cos", "cos_host.py")])
def test_generated_codex_timeout_and_owned_legacy_migration(tmp_path, old_name, old_host):
    for relative in ("src/engine/.venv/Scripts/python.exe", "src/cos/codex_host.py"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    current = settings(tmp_path)
    assert current["tool_timeout_sec"] == 240
    old = dict(current, tool_timeout_sec=600, args=[*current["args"][:-1], str(path.with_name(old_host))])
    target = tmp_path / "config.toml"
    original = "title = 'keep'\n" + codex_toml(old).replace("mcp_servers.rhino", "mcp_servers." + old_name)
    target.write_text(original, encoding="utf-8")
    backup = install_codex(target, current)
    assert backup.read_text(encoding="utf-8") == original
    assert tomllib.loads(target.read_text(encoding="utf-8")) == {"title": "keep", "mcp_servers": {"rhino": current}}
    assert install_codex(target, current) is None
    target.write_text(codex_toml(dict(current, tool_timeout_sec=30)), encoding="utf-8")
    before = target.read_bytes()
    with pytest.raises(ValueError):
        install_codex(target, current)
    assert target.read_bytes() == before
