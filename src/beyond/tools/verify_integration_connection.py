"""Verify and release a Beyond connection to the Rhino started for acceptance."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

import almond_mcp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[3]
BEYOND = ROOT / "src/beyond"
HOST = BEYOND / "codex_host.py"
sys.path.insert(0, str(BEYOND))
from winpipe import read_hosts


async def call(client, name, arguments):
    reply = await client.call_tool(name, arguments)
    if reply.is_error or not isinstance(reply.structured_content, dict):
        detail = " ".join(item.text for item in reply.content if item.type == "text")
        raise RuntimeError(f"{name}: {detail or 'invalid Beyond response'}")
    return reply.structured_content


def has_model(record, model):
    path = record.get("model_path")
    return bool(path) and Path(path).resolve() == model


async def verify_connection(client, pid, start_ticks, model):
    try:
        async with asyncio.timeout(30):
            while True:
                # The public listing exposes host IDs. The local advertisement
                # establishes the process identity independently of that reply.
                host_ids = {
                    record["host_id"] for record in read_hosts(BEYOND / "data")
                    if record["pid"] == pid and str(record["process_start_ticks"]) == start_ticks
                }
                inventory = await call(client, "connect_01-list_up", {})
                targets = [target for target in inventory["targets"] if target.get("host_id") in host_ids]
                if targets:
                    break
                await asyncio.sleep(0.25)
    except TimeoutError as exc:
        raise RuntimeError(f"Beyond did not discover Rhino PID {pid} for {model}.") from exc

    if len(targets) != 1:
        raise RuntimeError(f"Beyond advertised more than one target for Rhino PID {pid}.")
    target = targets[0]
    if target.get("state") != "available":
        raise RuntimeError(f"Rhino PID {pid} is {target.get('state')}: {target.get('reason')}")
    if not has_model(target, model):
        raise RuntimeError(f"Beyond discovered the wrong model for Rhino PID {pid}: {target.get('model_path')}")

    connection = await call(client, "connect_02-session", {
        "host_id": target["host_id"], "model_path": target["model_path"],
    })
    connection_id = connection.get("connection_id")
    if not isinstance(connection_id, str) or not connection_id:
        raise RuntimeError("Beyond did not return a connection_id for the verification connection.")
    try:
        inventory = await call(client, "connect_01-list_up", {})
        bound = next((row for row in inventory["targets"] if row.get("connection_id") == connection_id), {})
        if (connection.get("state") != "ready" or bound.get("state") != "ready"
                or bound.get("host_id") != target["host_id"] or not has_model(bound, model)):
            raise RuntimeError("Beyond did not bind the intended Rhino PID and test model.")
    finally:
        released = await call(client, "connect_04-disconnect", {"connection_id": connection_id})
        if not released.get("released"):
            raise RuntimeError("Beyond did not release the verification connection.")

    return {"host_id": target["host_id"], "pid": pid, "process_start_ticks": start_ticks,
            "model_path": str(model), "state": "ready", "released": True}


async def verify(pid, start_ticks, model):
    # Keep the desktop relay's supported launch flags and the worktree's editable install.
    environment = {name: value for name, value in os.environ.items()
                   if not name.upper().startswith("PYTHON")}
    params = StdioServerParameters(
        command=sys.executable, args=["-B", "-X", "utf8", str(HOST)], cwd=ROOT, env=environment,
    )
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=60) as client:
            if (await client.initialize()).server_info.name != "beyond":
                raise RuntimeError("The worktree MCP server did not identify itself as Beyond.")
            return await verify_connection(client, pid, start_ticks, model)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-environment", action="store_true")
    parser.add_argument("--pid", type=int)
    parser.add_argument("--start-ticks")
    parser.add_argument("--model", type=Path)
    args = parser.parse_args()
    if Path(almond_mcp.__file__).resolve().parent != ROOT / "src/mcp":
        parser.exit(1, "Almond Python sources do not belong to this worktree. Rebuild its environment.\n")
    if args.check_environment:
        return
    if not all((args.pid, args.start_ticks, args.model)):
        parser.error("--pid, --start-ticks and --model are required for connection verification")
    print(json.dumps(asyncio.run(verify(args.pid, args.start_ticks, args.model.resolve(strict=True)))))


if __name__ == "__main__":
    main()
