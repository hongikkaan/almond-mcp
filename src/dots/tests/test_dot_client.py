"""Offline tests for the dot client; no Rhino, model, or DB access."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import AsyncMock
from mcp.types import Tool, CallToolResult, TextContent

spec = importlib.util.spec_from_file_location("dot_client", Path(__file__).parents[1] / "dot_client.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DotClientTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = AsyncMock()
        self.tool = Tool(name="example", description="Exact description", inputSchema={"type": "object"})
        self.client = module.DotClient(self.session, [self.tool])

    async def test_catalog_does_not_call_server_again(self):
        self.assertEqual((await self.client.dispatch({"op": "catalog"}))["names"], ["example"])
        self.session.list_tools.assert_not_called()

    async def test_describe_keeps_exact_schema(self):
        result = await self.client.dispatch({"op": "describe", "names": ["example"]})
        self.assertEqual(result["tools"][0]["description"], "Exact description")
        self.assertEqual(result["tools"][0]["inputSchema"], {"type": "object"})

    async def test_invalid_requests_do_not_call(self):
        for value in [[], {"op": "describe", "names": "example"}, {"op": "describe", "names": ["missing"]}, {"op": "call", "name": "example", "arguments": []}, {"op": "call", "name": "missing"}]:
            with self.assertRaises(ValueError):
                await self.client.dispatch(value)
        self.session.call_tool.assert_not_called()

    async def test_call_preserves_result_and_arguments(self):
        self.session.call_tool.return_value = CallToolResult(content=[TextContent(type="text", text="raw")], structuredContent={"value": 3}, isError=True)
        args = {"sections": ["document"]}
        result = await self.client.dispatch({"op": "call", "name": "example", "arguments": args})
        self.assertTrue(result["tool_result"]["isError"])
        self.assertEqual(result["tool_result"]["structuredContent"], {"value": 3})
        self.session.call_tool.assert_awaited_once_with("example", args)

    async def test_call_exception_is_not_retried(self):
        self.session.call_tool.side_effect = TimeoutError("uncertain")
        with self.assertRaises(TimeoutError):
            await self.client.dispatch({"op": "call", "name": "example"})
        self.session.call_tool.assert_awaited_once()

    async def test_caller_must_pass_id_even_after_successful_connection(self):
        connect, observe = "connect_02-session", "example"
        tools = [Tool(name=connect, inputSchema={"type": "object"}),
                 Tool(name=observe, inputSchema={"type": "object", "required": ["connection_id"]})]
        client = module.DotClient(self.session, tools)
        missing = "connection_id가 지정되지 않았습니다"
        self.session.call_tool.side_effect = [
            CallToolResult(content=[], structuredContent={"connection_id": "A"}),
            CallToolResult(content=[TextContent(type="text", text=missing)], isError=True),
            CallToolResult(content=[]),
        ]
        await client.dispatch({"op": "call", "name": connect, "arguments": {}})
        reply = await client.dispatch({"op": "call", "name": observe})
        self.assertTrue(reply["tool_result"]["isError"])
        self.assertEqual(reply["tool_result"]["content"][0]["text"], missing)
        self.session.call_tool.assert_awaited_with(observe, {})
        await client.dispatch({"op": "call", "name": observe, "arguments": {"connection_id": "B"}})
        self.session.call_tool.assert_awaited_with(observe, {"connection_id": "B"})

    async def test_explicit_variable_tracks_only_successful_connections(self):
        connect, start, drop = "connect_02-session", "connect_03-start_session", "connect_04-disconnect"
        tools = [Tool(name=n, inputSchema={"type": "object", "required": fields})
                 for n, fields in [(connect, []), (start, []), (drop, ["connection_id"])]]
        client = module.DotClient(self.session, tools)

        async def call(name, arguments, expected, result, *, error=False):
            self.session.call_tool.return_value = CallToolResult(content=[], structuredContent=result, isError=error)
            await client.dispatch({"op": "call", "name": name, "arguments": arguments})
            self.session.call_tool.assert_awaited_with(name, expected)

        ref = {"connection_id": "$connection_id"}
        a, b = {"connection_id": "A"}, {"connection_id": "B"}
        await call(drop, ref, {"connection_id": ""}, {}, error=True)
        await call(connect, {}, {}, a)
        await call(start, {}, {}, b, error=True)
        await call(drop, ref, a, {}, error=True)
        await call(start, {}, {}, b)
        await call(drop, a, a, {"released": True})
        await call(drop, {"connection_id": ""}, {"connection_id": ""}, {}, error=True)
        await call(drop, ref, b, {"released": True})
        await call(drop, ref, {"connection_id": ""}, {}, error=True)


if __name__ == "__main__":
    unittest.main()
