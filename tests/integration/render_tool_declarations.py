"""Publish the beyond and RhinoTerminal stdio catalogs as reproducible Markdown."""
import asyncio
from contextlib import asynccontextmanager
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


def render_catalogs(beyond, terminal):
    lines = ["# 현행 툴 선언", "",
             "beyond와 RhinoTerminal의 `tools/list`에서 읽은 설명과 입출력 스키마다. "
             "공통 값은 한 번만 표시한다. 각 해시는 도구를 이름순으로 정렬하고 객체 키를 정렬한 뒤, "
             "공백과 유니코드 이스케이프 없이 UTF-8 JSON으로 직렬화한 전체 배열에서 계산한다.", ""]
    catalogs = (("beyond", beyond), ("RhinoTerminal", terminal))
    for route, tools in catalogs:
        catalog = [tools[name] for name in sorted(tools)]
        encoded = json.dumps(catalog, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        lines.append(f"- {route} 도구 {len(catalog)}개, 선언 SHA-256 `{hashlib.sha256(encoded).hexdigest()}`")
    for index, name in enumerate(sorted(beyond.keys() | terminal.keys()), 1):
        lines.extend(["", f"### {index}. {name}", ""])
        for field, label in (("description", "설명"), ("inputSchema", "입력 스키마"), ("outputSchema", "출력 스키마")):
            values = [(route, tools[name][field]) for route, tools in catalogs if name in tools]
            if len(values) == 2 and values[0][1] == values[1][1]:
                values = [("beyond · RhinoTerminal", values[0][1])]
            for route, value in values:
                if field == "description":
                    lines.extend([f"**{route}**", "", "```txt", value, "```", ""])
                else:
                    lines.extend([f"<details><summary>{route} {label}</summary>", "", "```json",
                                  json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2),
                                  "```", "", "</details>", ""])
    return "\n".join(lines).rstrip() + "\n"


def isolated_environment(directory, checkout=ROOT):
    env = dict(os.environ)
    for variable in env.copy():
        if variable.startswith(("ALMOND_", "ALMONDRHINO_", "RHINO_MCP_")):
            del env[variable]
    env.update(ALMOND_TEST_ROOT=str(directory), RHINO_MCP_STATE_DB=str(directory / "direct.sqlite3"),
               PYTHONPATH=os.pathsep.join(str(checkout / path) for path in ("src/mcp", "src/mcp/runtime", "src/beyond")),
               FASTMCP_CHECK_FOR_UPDATES="off")
    for variable in paths.LIBRARY_DIRS:
        location = directory / variable
        location.mkdir(parents=True, exist_ok=True)
        env[variable] = str(location)
    return env


def stdio_parameters(route, directory, checkout=ROOT, *, model_name="disposable.3dm"):
    env = isolated_environment(directory, checkout)
    if route == "beyond":
        entry = ["-c", "import os; from pathlib import Path; from codex_host import main; "
                       "main(Path(os.environ['ALMOND_TEST_ROOT']))"]
    elif route == "terminal":
        model = directory / model_name
        if model.name != model_name or ":" in model_name or model.suffix.lower() != ".3dm":
            raise ValueError("The fixture needs a .3dm filename inside its temporary directory")
        model.touch(exist_ok=False)
        entry = [str(ROOT / "tests/integration/bound_server_fixture.py"), model.name]
    elif route == "standalone":
        entry = ["-c", "from almond_mcp.server import mcp; mcp.run()"]
    else:
        raise ValueError(f"Unsupported stdio route: {route}")
    return StdioServerParameters(command=sys.executable, args=["-B", "-X", "utf8", "-u", *entry],
                                 env=env, cwd=checkout)


@asynccontextmanager
async def open_stdio(params):
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=45.0) as client:
            yield client, await client.initialize()


async def read_catalog(params):
    async with open_stdio(params) as (client, initialized):
        tools = {t.name: t.model_dump(mode="json", by_alias=True, exclude_none=True)
                 for t in (await client.list_tools()).tools}
        return initialized, tools


if __name__ == "__main__":
    scratch = ROOT / "data/t"
    scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=scratch, prefix="tools-") as temporary:
        _, beyond = asyncio.run(read_catalog(stdio_parameters("beyond", Path(temporary) / "beyond")))
        _, terminal = asyncio.run(read_catalog(stdio_parameters("terminal", Path(temporary) / "terminal")))
    (ROOT / "TOOL-DECLARATIONS-CURRENT.md").write_text(render_catalogs(beyond, terminal), encoding="utf-8", newline="\n")
