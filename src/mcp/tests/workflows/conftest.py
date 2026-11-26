import asyncio
import json

import pytest
from fastmcp import Client


@pytest.fixture
def call_tool():
    def call(server, tool, **arguments):
        async def request():
            async with Client(server) as client:
                return await client.call_tool(tool, arguments, raise_on_error=False)

        result = asyncio.run(request())
        structured = result.structured_content
        if structured is not None:
            wrapped = structured.get("result")
            return result, json.loads(wrapped) if isinstance(wrapped, str) else structured
        return result, json.loads(result.content[0].text)

    return call
