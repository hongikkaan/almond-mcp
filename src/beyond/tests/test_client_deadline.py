"""Generated registration and timeout maintenance for the direct Codex host."""
import sys
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from client_config import codex_toml, install_codex, settings


@pytest.fixture
def current(tmp_path):
    for relative in ("src/engine/.venv/Scripts/python.exe", "src/beyond/codex_host.py"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    return settings(tmp_path)


def test_new_codex_config_uses_the_canonical_beyond_host(tmp_path, current):
    assert current["tool_timeout_sec"] == 240
    assert Path(current["args"][-1]) == tmp_path / "src/beyond/codex_host.py"
    target = tmp_path / "config.toml"
    assert install_codex(target, current) is None
    assert tomllib.loads(target.read_text(encoding="utf-8")) == {"mcp_servers": {"rhino": current}}


@pytest.mark.parametrize("folder", ["beyond", "cos"])
def test_generated_direct_settings_update_only_the_old_timeout(tmp_path, current, folder):
    direct = dict(current, args=[*current["args"][:-1], str(tmp_path / "src" / folder / "codex_host.py")])
    target = tmp_path / "config.toml"
    original = "title = 'keep'\n" + codex_toml(dict(direct, tool_timeout_sec=600))
    original = original.replace("tool_timeout_sec = 600", "tool_timeout_sec = 600 # keep this comment")
    target.write_text(original, encoding="utf-8")
    backup = install_codex(target, current)
    assert backup.read_text(encoding="utf-8") == original
    expected = original.replace("tool_timeout_sec = 600", "tool_timeout_sec = 240")
    assert target.read_text(encoding="utf-8") == expected
    assert install_codex(target, current) is None
    assert target.read_text(encoding="utf-8") == expected
    assert list(tmp_path.glob("config.toml.almond-backup-*")) == [backup]


def test_customized_direct_settings_are_untouched(tmp_path, current):
    target = tmp_path / "config.toml"
    target.write_text(codex_toml(dict(current, tool_timeout_sec=30)), encoding="utf-8")
    before = target.read_bytes()
    with pytest.raises(ValueError, match="different settings"):
        install_codex(target, current)
    assert target.read_bytes() == before
    assert not list(tmp_path.glob("config.toml.almond-backup-*"))
