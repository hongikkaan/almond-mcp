"""Reuse the COS stdio host from Codex or another local MCP client.

Printing configuration is the default. --install-codex explicitly adds a new
entry, preserves all other settings and refuses to replace a conflicting entry.
This module does not import Almond, start a host, or touch a Rhino document.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import tomllib

NAME = "almond_cos"
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
    host = root / "src/cos/cos_host.py"
    for path in (python, host):
        if not path.is_file():
            raise ValueError(f"Missing runtime file: {path}. Set up this installation first.")
    return {
        "command": str(python),
        "args": ["-B", "-X", "utf8", "-u", str(host)],
        "cwd": str(root),
        "startup_timeout_sec": 120,
        "tool_timeout_sec": 600,
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


def install_codex(path: Path, config: dict) -> Path | None:
    path = path.expanduser().resolve()
    original = path.read_bytes() if path.exists() else b""
    text = original.decode("utf-8-sig")
    parsed = tomllib.loads(text)
    existing = parsed.get("mcp_servers", {}).get(NAME)
    if existing is not None:
        if existing == config:
            return None
        raise ValueError(f"{NAME} already exists with different settings in {path}; no changes made.")
    updated = text.rstrip() + "\n\n" + codex_toml(config)
    expected = dict(parsed)
    expected["mcp_servers"] = dict(parsed.get("mcp_servers", {}), **{NAME: config})
    if tomllib.loads(updated) != expected:
        raise ValueError("Cannot append the MCP table without changing existing settings.")
    if not path.parent.is_dir():
        raise ValueError(f"Config directory does not exist: {path.parent}")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".almond-",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
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
                        help="Explicitly add almond_cos to this config (backup existing file).")
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
            print("Restart the MCP client. Only one COS/Codex stdio host may use this checkout at a time.")
        else:
            print(codex_toml(config) if args.format == "codex" else generic_json(config, os.environ), end="")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
