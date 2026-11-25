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


def test_generated_direct_settings_update_only_the_old_timeout(tmp_path, current):
    target = tmp_path / "config.toml"
    original = "title = 'keep'\n" + codex_toml(dict(current, tool_timeout_sec=600))
    original = original.replace("tool_timeout_sec = 600", "tool_timeout_sec = 600 # keep this comment")
    target.write_text(original, encoding="utf-8")
    backup = install_codex(target, current)
    assert backup.read_text(encoding="utf-8") == original
    expected = original.replace("tool_timeout_sec = 600", "tool_timeout_sec = 240")
    assert target.read_text(encoding="utf-8") == expected
    assert install_codex(target, current) is None
    assert target.read_text(encoding="utf-8") == expected
    assert list(tmp_path.glob("config.toml.almond-backup-*")) == [backup]


@pytest.mark.parametrize("setting", ["tool_timeout_sec", "args"])
def test_customized_direct_settings_are_untouched(tmp_path, current, setting):
    target = tmp_path / "config.toml"
    overrides = {"tool_timeout_sec": 30, "args": [*current["args"][:-1], str(tmp_path / "custom_host.py")]}
    target.write_text(codex_toml(dict(current, **{setting: overrides[setting]})), encoding="utf-8")
    before = target.read_bytes()
    with pytest.raises(ValueError, match="different settings"):
        install_codex(target, current)
    assert target.read_bytes() == before
    assert not list(tmp_path.glob("config.toml.almond-backup-*"))


def _old_entry(current, host_name="cos_host.py", name="almond_cos", **overrides):
    host = Path(current["cwd"]) / "src/cos" / host_name
    legacy = dict(current, args=[*current["args"][:-1], str(host)], tool_timeout_sec=600)
    legacy.update(overrides)
    return codex_toml(legacy).replace("[mcp_servers.rhino", f"[mcp_servers.{name}")


@pytest.mark.parametrize("timeout", [240, 600])
@pytest.mark.parametrize("host_name", ["cos_host.py", "codex_host.py"])
@pytest.mark.parametrize("name", ["almond_cos", "rhino"])
def test_migrates_generated_old_server(tmp_path, current, timeout, host_name, name):
    target = tmp_path / "config.toml"
    unrelated = '[mcp_servers.other]\ncommand = "other"\n'
    legacy = _old_entry(current, host_name, name, tool_timeout_sec=timeout)
    legacy = legacy.replace(f"[mcp_servers.{name}]", f"[mcp_servers.{name}] # server")
    legacy = legacy.replace('PYTHONUTF8 = "1"', 'PYTHONUTF8 = "1" # environment')
    before = ("\ufefftitle = 'keep'\n\n" + legacy + "\n" + unrelated).replace("\n", "\r\n").encode()
    target.write_bytes(before)

    backup = install_codex(target, current)

    assert backup is not None and backup.read_bytes() == before
    text = target.read_bytes().decode("utf-8-sig")
    assert target.read_bytes().startswith(b"\xef\xbb\xbf")
    assert unrelated.replace("\n", "\r\n") in text
    assert "[mcp_servers.rhino] # server\r\n" in text
    assert 'PYTHONUTF8 = "1" # environment\r\n' in text
    assert tomllib.loads(text) == {"title": "keep", "mcp_servers": {"rhino": current, "other": {"command": "other"}}}
    assert install_codex(target, current) is None
    assert list(tmp_path.glob("config.toml.almond-backup-*")) == [backup]


@pytest.mark.parametrize("old_direct", [False, True])
def test_removes_generated_duplicate(tmp_path, current, old_direct):
    target = tmp_path / "config.toml"
    direct = _old_entry(current, "codex_host.py", "rhino") if old_direct else codex_toml(current)
    legacy = _old_entry(current).replace("startup_timeout_sec = 120", "startup_timeout_sec = 120 # startup")
    unrelated = '[mcp_servers.other]\ncommand = "other"\n'
    before = direct + "\n" + legacy + "# keep\n\n" + unrelated
    target.write_bytes(before.encode())

    backup = install_codex(target, current)

    assert backup is not None and backup.read_bytes() == before.encode()
    text = target.read_text(encoding="utf-8")
    assert text.startswith(codex_toml(current))
    assert "# startup\n" in text and "# keep\n\n" + unrelated in text
    assert tomllib.loads(text) == {"mcp_servers": {"rhino": current, "other": {"command": "other"}}}
    assert install_codex(target, current) is None
    assert list(tmp_path.glob("config.toml.almond-backup-*")) == [backup]


@pytest.mark.parametrize("case", ["custom_legacy", "custom_direct", "unrelated_host", "quoted_legacy"])
def test_ambiguous_legacy_setup_stops_before_write(tmp_path, current, case):
    target = tmp_path / "config.toml"
    entries = {
        "custom_legacy": _old_entry(current, tool_timeout_sec=45),
        "custom_direct": _old_entry(current) + "\n" + _old_entry(current, "codex_host.py", "rhino", tool_timeout_sec=45),
        "unrelated_host": _old_entry(current, args=["-u", "custom_host.py"]),
        "quoted_legacy": _old_entry(current).replace("[mcp_servers.almond_cos]", '[mcp_servers."almond_cos"]'),
    }
    before = entries[case].encode()
    target.write_bytes(before)

    with pytest.raises(ValueError, match=r"almond_cos.*rhino.*settings"):
        install_codex(target, current)

    assert target.read_bytes() == before
    assert not list(tmp_path.glob("config.toml.almond-*"))
