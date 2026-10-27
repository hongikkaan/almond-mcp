"""Configure the direct stdio entry for Codex or another local MCP client.

Printing configuration is the default. --install-codex explicitly adds a new
entry or migrates its exact previous entry, and preserves all other settings.
This module does not import Almond, start a host, or touch a Rhino document.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import tomllib

NAME = "rhino"
LEGACY_NAME = "almond_cos"
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
    host = root / "src/cos/codex_host.py"
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
    servers = parsed.get("mcp_servers", {})
    existing = servers.get(NAME)
    legacy = servers.get(LEGACY_NAME)
    old_config = dict(config, args=[*config["args"][:-1],
                                  str(Path(config["args"][-1]).with_name("cos_host.py"))])
    supported = (config, old_config)
    if legacy is not None:
        if existing is not None or legacy not in supported:
            raise ValueError(f"Conflicting or customized {LEGACY_NAME}/{NAME} settings in {path}; no changes made.")
        # Only migrate our exact old generated configuration. Preserve the
        # surrounding text/comments and validate its parsed meaning afterward.
        updated = re.sub(r"(?m)^(\s*\[mcp_servers\.)almond_cos(?=(?:\.env)?\])",
                         lambda match: match.group(1) + NAME, text)
        expected_servers = dict(servers)
        expected_servers.pop(LEGACY_NAME)
        expected_servers[NAME] = config
    else:
        expected_servers = dict(servers, **{NAME: config})
        updated = text.rstrip() + "\n\n" + codex_toml(config)
    if existing is not None:
        if existing == config:
            return None
        if existing != old_config:
            raise ValueError(f"{NAME} already exists with different settings in {path}; no changes made.")
        updated = text
    if (legacy if legacy is not None else existing) == old_config:
        # Only the generated one-line args assignment is replaced. Reject any
        # unfamiliar syntax rather than rewriting unrelated tables or comments.
        header = re.search(r"(?m)^\[mcp_servers\.rhino\][ \t]*\r?$", updated)
        if header is None:
            raise ValueError("Cannot locate the owned rhino table; no changes made.")
        end = re.search(r"(?m)^\s*\[", updated[header.end():])
        stop = header.end() + end.start() if end else len(updated)
        old_args = json.dumps(old_config["args"], ensure_ascii=False)
        pattern = r"(?m)^(args[ \t]*=[ \t]*)" + re.escape(old_args) + r"([ \t]*(?:#[^\r\n]*)?)(\r?)$"
        body, count = re.subn(pattern,
                             lambda match: match[1] + json.dumps(config["args"], ensure_ascii=False) + match[2] + match[3],
                             updated[header.end():stop])
        if count != 1:
            raise ValueError("Cannot safely migrate the owned host arguments; no changes made.")
        updated = updated[:header.end()] + body + updated[stop:]
    expected = dict(parsed)
    expected["mcp_servers"] = expected_servers
    if tomllib.loads(updated) != expected:
        raise ValueError("Cannot update the MCP table without changing existing settings.")
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
                        help="Add rhino or migrate the exact legacy almond_cos entry (backup existing file).")
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
            print("Call start_session with a saved model path and a unique request_id to open an independent session.")
        else:
            print(codex_toml(config) if args.format == "codex" else generic_json(config, os.environ), end="")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
