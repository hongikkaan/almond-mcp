"""Configure the direct stdio entry for Codex or another local MCP client.

Printing configuration is the default. --install-codex adds or updates the
direct entry and migrates an earlier generated registration.
This module does not import Almond, start a host, or touch a Rhino document.
"""
from __future__ import annotations

import argparse
from codecs import BOM_UTF8
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import tomllib

NAME = "rhino"
_LEGACY_NAME = "almond_cos"
_OLD_TOOL_TIMEOUT = 600
ENV_VARS = (
    "LOCALAPPDATA", "TEMP", "TMP", "TMPDIR",
    "RHINO_MCP_LIBRARY_DIR", "RHINO_MCP_DRAWING_ASSET_DIR",
    "RHINO_MCP_DIAGRAM_ASSET_DIR", "RHINO_MCP_GENERATED_ASSET_DIR",
    "RHINO_MCP_DRAWING_RECIPE_DIR", "RHINO_MCP_DRAFTING_DIR",
    "RHINO_MCP_CAPSULE_DIR", "RHINO_MCP_MATERIAL_DIR",
    "RHINO_MCP_CONSTRUCTION_DIR", "RHINO_MCP_HISTORY_DIR",
)


def settings(root: Path) -> dict:
    root = root.resolve()
    python = root / "src/engine/.venv/Scripts/python.exe"
    host = root / "src/beyond/codex_host.py"
    for path in (python, host):
        if not path.is_file():
            raise ValueError(f"Missing runtime file: {path}. Set up this installation first.")
    return {
        "command": str(python),
        "args": ["-B", "-X", "utf8", "-u", str(host)],
        "cwd": str(root),
        "startup_timeout_sec": 120,
        "tool_timeout_sec": 240,
        "env_vars": list(ENV_VARS),
        "env": {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    }


def codex_toml(config: dict) -> str:
    # JSON strings/arrays used here are also valid TOML values, including paths.
    lines = [f"[mcp_servers.{NAME}]"]
    for key, value in config.items():
        if key != "env":
            lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
    lines.extend(["", f"[mcp_servers.{NAME}.env]"])
    lines.extend(f"{key} = {json.dumps(value)}" for key, value in config["env"].items())
    return "\n".join(lines) + "\n"


def generic_json(config: dict, environment: dict) -> str:
    # env_vars is Codex-specific; ordinary clients get the explicit allowlist.
    env = {key: environment[key] for key in ENV_VARS if key in environment}
    env.update(config["env"])
    server = {key: config[key] for key in ("command", "args", "cwd")}
    server["env"] = env
    return json.dumps({"mcpServers": {NAME: server}}, ensure_ascii=False, indent=2) + "\n"


def _edit_table(text: str, table: str, before: dict, after: dict | None, destination: str) -> str:
    # Limit edits to generated lines and keep comments when removing duplicates.
    line_end = r"(?P<space>[ \t]*)(?P<comment>#[^\r\n]*)?(?P<eol>\r?\n|\Z)"
    header = re.search(rf"(?m)^(?P<indent>[ \t]*)\[{re.escape(table)}\]" + line_end, text)
    if header is None:
        raise ValueError(f"Cannot locate the generated [{table}] table.")

    end = re.search(r"(?m)^[ \t]*\[", text[header.end():])
    stop = header.end() + end.start() if end else len(text)
    body = text[header.end():stop]

    def keep_comment(match):
        if match["comment"] is None:
            return ""
        return match["indent"] + match["comment"] + match["eol"]

    for key, value in before.items():
        if after is not None and value == after[key]:
            continue

        old = re.escape(json.dumps(value, ensure_ascii=False))
        assignment = rf"(?m)^(?P<indent>[ \t]*)(?P<assignment>{re.escape(key)}[ \t]*=[ \t]*)"

        def replace(match):
            if after is None:
                return keep_comment(match)
            new = json.dumps(after[key], ensure_ascii=False)
            return (match["indent"] + match["assignment"] + new + match["space"]
                    + (match["comment"] or "") + match["eol"])

        body, count = re.subn(assignment + old + line_end, replace, body)
        if count != 1:
            raise ValueError(f"Cannot safely update the generated {key} in [{table}].")

    if after is None:
        heading = keep_comment(header)
    else:
        heading = header[0].replace(f"[{table}]", f"[{destination}]", 1)
    return text[:header.start()] + heading + body + text[stop:]


def _edit_entry(text: str, name: str, before: dict, after: dict | None) -> str:
    table = f"mcp_servers.{name}"
    direct = f"mcp_servers.{NAME}"
    values = {key: value for key, value in before.items() if key != "env"}
    text = _edit_table(text, table, values, after, direct)
    if name == NAME:
        return text

    env = after["env"] if after is not None else None
    return _edit_table(text, f"{table}.env", before["env"], env, f"{direct}.env")


def _prior_entries(config: dict) -> tuple[dict, ...]:
    # Both historical script names belong to the same checkout as the new host.
    old_dir = Path(config["cwd"]) / "src/cos"
    return tuple(
        dict(config, args=[*config["args"][:-1], str(old_dir / host)], tool_timeout_sec=timeout)
        for host in ("cos_host.py", "codex_host.py")
        for timeout in (config["tool_timeout_sec"], _OLD_TOOL_TIMEOUT)
    )


def _is_generated(entry: dict, supported: tuple[dict, ...]) -> bool:
    # TOML floats compare equal to integers in Python.
    return entry in supported and all(type(entry[key]) is int for key in ("startup_timeout_sec", "tool_timeout_sec"))


def _update_codex(text: str, path: Path, config: dict) -> str:
    parsed = tomllib.loads(text)
    servers = parsed.get("mcp_servers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"Expected a table for mcp_servers in {path}.")

    existing = servers.get(NAME)
    legacy = servers.get(_LEGACY_NAME)
    expected_servers = dict(servers, **{NAME: config})
    expected_servers.pop(_LEGACY_NAME, None)
    expected = dict(parsed, mcp_servers=expected_servers)

    try:
        prior = _prior_entries(config)
        supported = (*prior, config, dict(config, tool_timeout_sec=_OLD_TOOL_TIMEOUT))
        if existing is not None and not _is_generated(existing, supported):
            raise ValueError(f"{NAME} already exists with different settings in {path}; no changes made.")
        if legacy is not None and not _is_generated(legacy, prior):
            raise ValueError("The previous entry differs from the generated registration.")

        updated = text
        if existing is not None and legacy is not None:
            updated = _edit_entry(updated, _LEGACY_NAME, legacy, None)

        source = NAME if existing is not None else _LEGACY_NAME
        entry = existing if existing is not None else legacy
        if entry is None:
            updated = text.rstrip() + "\n\n" + codex_toml(config)
        elif source != NAME or entry != config:
            updated = _edit_entry(updated, source, entry, config)

        if tomllib.loads(updated) != expected:
            raise ValueError("Cannot update the MCP table without changing existing settings.")
        return updated
    except ValueError as exc:
        if legacy is None:
            if existing is None:
                raise
            raise ValueError(
                f"{exc}\nReview [mcp_servers.{NAME}] in {path}. For an older direct connection, "
                f"set the host argument to {config['args'][-1]} and keep the other settings."
            ) from exc
        raise ValueError(
            f"Cannot migrate [{_LEGACY_NAME}] to [{NAME}] with the settings in {path}. {exc}\n"
            f"Review both MCP tables and their .env sections. Keep needed direct-connection settings "
            f"in [mcp_servers.{NAME}] and set its host argument to {config['args'][-1]}. "
            f"Remove the retired [mcp_servers.{_LEGACY_NAME}] entry or rename it if it is a different server."
        ) from exc


def install_codex(path: Path, config: dict) -> Path | None:
    path = path.expanduser().resolve()
    original = path.read_bytes() if path.exists() else b""
    text = original.decode("utf-8-sig")
    updated = _update_codex(text, path, config)
    if updated == text:
        return None

    if not path.parent.is_dir():
        raise ValueError(f"Config directory does not exist: {path.parent}")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".almond-",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            if original.startswith(BOM_UTF8):
                stream.write(BOM_UTF8)
            stream.write(updated.encode("utf-8"))
        if (path.read_bytes() if path.exists() else b"") != original:
            raise ValueError("Codex config changed during setup; no changes made. Run setup again.")
        backup = None
        if path.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = path.with_name(path.name + ".almond-backup-" + stamp)
            with backup.open("xb") as stream:
                stream.write(original)
        os.replace(temporary, path)
        return backup
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=Path(__file__).resolve().parents[2],
                        help="Daily installation checkout, never a development worktree.")
    parser.add_argument("--format", choices=("codex", "json"), default="codex")
    parser.add_argument("--install-codex", type=Path, metavar="CONFIG_TOML",
                        help="Install or update the rhino entry and migrate its earlier generated registration.")
    args = parser.parse_args()
    if args.install_codex and args.format != "codex":
        parser.error("--install-codex requires --format codex")
    try:
        config = settings(args.runtime_root)
        if args.install_codex:
            backup = install_codex(args.install_codex, config)
            print(f"Codex configuration ready: {args.install_codex}")
            if backup:
                print(f"Original configuration backup: {backup}")
            print("Reload the MCP client to use the lazy adapter. Registration does not start Rhino or a modeling worker.")
            print("Call connect_03-start_session tool with a saved model path and a unique request_id to open an independent session.")
        else:
            print(codex_toml(config) if args.format == "codex" else generic_json(config, os.environ), end="")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
