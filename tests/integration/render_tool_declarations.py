"""Publish the two offline stdio catalogs as readable, reproducible Markdown."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from almond_mcp import paths


ROOT = Path(__file__).resolve().parents[2]


def render_catalogs(cos, beyond):
    if cos.keys() != beyond.keys():
        raise ValueError("The two routes advertise different tool names.")
    lines = ["# 현행 툴 선언", "",
             "beyond와 CoS의 `tools/list`에서 읽은 설명 및 입출력 스키마다. "
             "두 경로의 값이 같으면 한 번만 표시한다.", ""]
    for route, tools in (("CoS", cos), ("beyond", beyond)):
        catalog = [tools[name] for name in sorted(tools)]
        encoded = json.dumps(catalog, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        lines.append(f"- {route} 선언 SHA-256: `{hashlib.sha256(encoded).hexdigest()}`")
    for index, name in enumerate(sorted(cos), 1):
        lines.extend(["", f"### {index}. {name}", ""])
        for field, label in (("description", "설명"), ("inputSchema", "입력 스키마"), ("outputSchema", "출력 스키마")):
            left, right = cos[name][field], beyond[name][field]
            values = [("CoS · beyond", left)] if left == right else [("CoS", left), ("beyond", right)]
            for route, value in values:
                if field == "description":
                    lines.extend([f"**{route}**", "", "```txt", value, "```", ""])
                else:
                    lines.extend([f"<details><summary>{route} {label}</summary>", "", "```json",
                                  json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2),
                                  "```", "", "</details>", ""])
    return "\n".join(lines).rstrip() + "\n"


async def read_route(client_name, directory):
    env = dict(os.environ)
    env.update(ALMOND_TEST_ROOT=str(directory), RHINO_MCP_STATE_DB=str(directory / "state.sqlite3"),
               PYTHONPATH=os.pathsep.join(str(ROOT / path) for path in ("src/mcp", "src/mcp/runtime", "src/cos")))
    for variable in paths.LIBRARY_DIRS:
        location = directory / variable
        location.mkdir(parents=True)
        env[variable] = str(location)
    code = ("import os; from pathlib import Path; from external_host import main; "
            f"main(Path(os.environ['ALMOND_TEST_ROOT']), client={client_name!r})")
    params = StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u", "-c", code], env=env)
    async with stdio_client(params) as (reader, writer), ClientSession(reader, writer) as client:
        await client.initialize()
        return {t.name: t.model_dump(mode="json", by_alias=True, exclude_none=True) for t in (await client.list_tools()).tools}


if __name__ == "__main__":
    with TemporaryDirectory() as temporary:
        cos = asyncio.run(read_route("cos", Path(temporary) / "cos"))
        beyond = asyncio.run(read_route("codex", Path(temporary) / "beyond"))
    (ROOT / "TOOL-DECLARATIONS-CURRENT.md").write_text(render_catalogs(cos, beyond), encoding="utf-8", newline="\n")
