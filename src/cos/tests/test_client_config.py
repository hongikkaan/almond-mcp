"""Generated client settings migrate only recognized, unedited owned values."""
from copy import deepcopy
import json
from pathlib import Path
import tomllib

import pytest

import client_config


GUIDANCE_VARIABLE = "ALMOND_GUIDANCE_FORMAT"
# The exact allowlist emitted before guidance format forwarding was added.
# Keep this independent of ENV_VARS so the migration fixtures remain historical.
PREVIOUS_ENV_VARS = [
    "LOCALAPPDATA", "TEMP", "TMP", "TMPDIR",
    "RHINO_MCP_LIBRARY_DIR", "RHINO_MCP_DRAWING_ASSET_DIR",
    "RHINO_MCP_DIAGRAM_ASSET_DIR", "RHINO_MCP_GENERATED_ASSET_DIR",
    "RHINO_MCP_DRAWING_RECIPE_DIR", "RHINO_MCP_DRAFTING_DIR",
    "RHINO_MCP_CAPSULE_DIR", "RHINO_MCP_MATERIAL_DIR",
    "RHINO_MCP_CONSTRUCTION_DIR", "RHINO_MCP_HISTORY_DIR",
]
PREFIX = (
    '# 사용자 설정: retain comments and unrelated servers\n'
    'model = "user-selected-model"\n'
    'model_reasoning_effort = "high" # keep this choice\n\n'
    '[mcp_servers.unrelated]\n'
    'command = "user-command"\n'
    'args = ["--user-argument"]\n'
    'env_vars = ["USER_ALLOWLIST"] # not the owned list\n\n'
)
SUFFIX = (
    '\n# Entries after the owned tables also remain byte-for-byte intact.\n'
    '[profiles.personal]\n'
    'model = "another-user-model"\n\n'
    '[mcp_servers.after]\n'
    'command = "another-command"\n'
    'args = ["cos_host.py", "ALMOND_GUIDANCE_FORMAT"]\n'
)


@pytest.fixture
def generated_config(tmp_path):
    root = tmp_path / "일상 설치"
    for relative in (
        "src/engine/.venv/Scripts/python.exe",
        "src/cos/codex_host.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    return client_config.settings(root)


def previous_config(config, *, old_host=False, old_environment=True):
    previous = deepcopy(config)
    if old_environment:
        previous["env_vars"] = PREVIOUS_ENV_VARS.copy()
    if old_host:
        previous["args"][-1] = str(Path(previous["args"][-1]).with_name("cos_host.py"))
    return previous


def owned_text(config, name="rhino"):
    return client_config.codex_toml(config).replace(
        "[mcp_servers.rhino", f"[mcp_servers.{name}"
    )


def write_original(tmp_path, text):
    path = tmp_path / "config.toml"
    original = text.encode("utf-8")
    path.write_bytes(original)
    return path, original


def assert_rejected_without_artifacts(path, original, config):
    before = {entry.name for entry in path.parent.iterdir()}
    with pytest.raises(ValueError):
        client_config.install_codex(path, config)
    assert path.read_bytes() == original
    assert {entry.name for entry in path.parent.iterdir()} == before
    assert not list(path.parent.glob(path.name + ".almond-*"))


def test_settings_forward_guidance_choice_without_changing_tool_exposure(generated_config):
    assert GUIDANCE_VARIABLE in client_config.ENV_VARS
    assert generated_config["env_vars"].count(GUIDANCE_VARIABLE) == 1
    assert set(generated_config["env_vars"]) == {*PREVIOUS_ENV_VARS, GUIDANCE_VARIABLE}
    assert "omit_tools_from" not in generated_config
    assert "omit_tools_from" not in client_config.codex_toml(generated_config)
    assert "omit_tools_from" not in client_config.generic_json(generated_config, {})


@pytest.mark.parametrize("delivery", ["fields", "sequential"])
def test_generic_json_forwards_only_allowed_parent_values(generated_config, delivery):
    parent = {
        GUIDANCE_VARIABLE: delivery,
        "TEMP": r"C:\user temp",
        "RHINO_MCP_LIBRARY_DIR": r"D:\library",
        "PYTHONUTF8": "0",
        "UNRELATED_PRIVATE_SETTING": "must not be forwarded",
    }
    output = json.loads(client_config.generic_json(generated_config, parent))
    server = output["mcpServers"]["rhino"]
    assert server == {
        "command": generated_config["command"],
        "args": generated_config["args"],
        "cwd": generated_config["cwd"],
        "env": {
            GUIDANCE_VARIABLE: delivery,
            "TEMP": parent["TEMP"],
            "RHINO_MCP_LIBRARY_DIR": parent["RHINO_MCP_LIBRARY_DIR"],
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
        },
    }
    assert parent["PYTHONUTF8"] == "0"


def test_generic_json_does_not_invent_an_unset_guidance_choice(generated_config):
    server = json.loads(client_config.generic_json(generated_config, {}))["mcpServers"]["rhino"]
    assert GUIDANCE_VARIABLE not in server["env"]


def test_install_new_generated_settings_does_not_enable_eager_tools(tmp_path, generated_config):
    path = tmp_path / "config.toml"
    assert client_config.install_codex(path, generated_config) is None
    assert tomllib.loads(path.read_text(encoding="utf-8")) == {
        "mcp_servers": {"rhino": generated_config}
    }
    assert "omit_tools_from" not in path.read_text(encoding="utf-8")
    assert {entry.name for entry in tmp_path.iterdir()} == {"config.toml", "일상 설치"}


@pytest.mark.parametrize(
    "name,old_host,old_environment",
    [
        ("rhino", False, True),
        ("rhino", True, True),
        ("almond_cos", True, True),
        # Retain the already-supported previous-host migration too.
        ("rhino", True, False),
        ("almond_cos", True, False),
    ],
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_migrate_exact_generated_variants_preserving_surroundings_and_backup(
    tmp_path, generated_config, name, old_host, old_environment, newline
):
    previous = previous_config(
        generated_config, old_host=old_host, old_environment=old_environment
    )
    table = owned_text(previous, name)
    table = table.replace(
        "args = " + json.dumps(previous["args"], ensure_ascii=False),
        "args = " + json.dumps(previous["args"], ensure_ascii=False) + " # host comment",
    ).replace(
        "env_vars = " + json.dumps(previous["env_vars"], ensure_ascii=False),
        "env_vars = " + json.dumps(previous["env_vars"], ensure_ascii=False) + " # allowlist comment",
    )
    text = (PREFIX + table + SUFFIX).replace("\n", newline)
    path, original = write_original(tmp_path, text)
    expected = text.replace("[mcp_servers.almond_cos", "[mcp_servers.rhino")
    for key in ("args", "env_vars"):
        expected = expected.replace(
            f"{key} = " + json.dumps(previous[key], ensure_ascii=False),
            f"{key} = " + json.dumps(generated_config[key], ensure_ascii=False),
            1,
        )

    backup = client_config.install_codex(path, generated_config)

    assert backup is not None
    assert backup.parent == path.parent
    assert backup.name.startswith(path.name + ".almond-backup-")
    assert backup.read_bytes() == original
    assert path.read_bytes() == expected.encode("utf-8")
    parsed = tomllib.loads(expected)
    assert parsed["mcp_servers"]["rhino"] == generated_config
    assert "almond_cos" not in parsed["mcp_servers"]
    assert set(parsed["mcp_servers"]) == {"unrelated", "rhino", "after"}
    assert {entry.name for entry in tmp_path.iterdir()} == {
        "config.toml", backup.name, "일상 설치"
    }


def test_latest_generated_settings_are_byte_unchanged_on_repeat(tmp_path, generated_config):
    path, original = write_original(tmp_path, PREFIX + owned_text(generated_config) + SUFFIX)
    before = {entry.name for entry in tmp_path.iterdir()}
    assert client_config.install_codex(path, generated_config) is None
    assert client_config.install_codex(path, generated_config) is None
    assert path.read_bytes() == original
    assert {entry.name for entry in tmp_path.iterdir()} == before


@pytest.mark.parametrize("name", ["rhino", "almond_cos"])
@pytest.mark.parametrize(
    "customization",
    ["startup_timeout", "tool_timeout", "env", "extra_env", "allowlist_removed",
     "allowlist_added", "args", "command", "cwd", "exposure"],
)
def test_customized_previous_settings_are_rejected_without_writing(
    tmp_path, generated_config, name, customization
):
    previous = previous_config(generated_config, old_host=True)
    if customization == "startup_timeout":
        previous["startup_timeout_sec"] += 1
    elif customization == "tool_timeout":
        previous["tool_timeout_sec"] += 1
    elif customization == "env":
        previous["env"]["PYTHONUTF8"] = "0"
    elif customization == "extra_env":
        previous["env"]["USER_OPTION"] = "preserve"
    elif customization == "allowlist_removed":
        previous["env_vars"].remove("TEMP")
    elif customization == "allowlist_added":
        previous["env_vars"].append("USER_OPTION")
    elif customization == "args":
        previous["args"].append("--user-option")
    elif customization == "command":
        previous["command"] = "user-python.exe"
    elif customization == "cwd":
        previous["cwd"] = str(tmp_path / "user-workspace")
    else:
        previous["omit_tools_from"] = ["deferred"]
    path, original = write_original(tmp_path, PREFIX + owned_text(previous, name) + SUFFIX)
    assert_rejected_without_artifacts(path, original, generated_config)


@pytest.mark.parametrize("name", ["rhino", "almond_cos"])
@pytest.mark.parametrize("key", ["args", "env_vars"])
@pytest.mark.parametrize("syntax", ["multiline", "custom-single-line"])
def test_unfamiliar_owned_value_syntax_is_rejected_even_when_semantically_generated(
    tmp_path, generated_config, name, key, syntax
):
    previous = previous_config(generated_config, old_host=True)
    encoded = json.dumps(previous[key], ensure_ascii=False)
    if syntax == "multiline":
        custom = "[\n" + "".join(
            "  " + json.dumps(value, ensure_ascii=False) + ",\n" for value in previous[key]
        ) + "]"
    else:
        # Valid TOML with the same values, but not the generated JSON-array form.
        custom = "[ " + ", ".join("'" + value + "'" for value in previous[key]) + " ]"
    table = owned_text(previous, name).replace(f"{key} = {encoded}", f"{key} = {custom}", 1)
    assert tomllib.loads(table)["mcp_servers"][name] == previous
    path, original = write_original(tmp_path, PREFIX + table + SUFFIX)
    assert_rejected_without_artifacts(path, original, generated_config)


def test_conflicting_current_and_legacy_owned_tables_are_preserved(tmp_path, generated_config):
    previous = previous_config(generated_config, old_host=True)
    path, original = write_original(
        tmp_path, PREFIX + owned_text(previous) + owned_text(previous, "almond_cos") + SUFFIX
    )
    assert_rejected_without_artifacts(path, original, generated_config)
