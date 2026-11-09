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

    async def test_call_preserves_result_and_connection(self):
        self.session.call_tool.return_value = CallToolResult(content=[TextContent(type="text", text="raw")], structuredContent={"value": 3}, isError=True)
        args = {"connection_id": "same-connection"}
        result = await self.client.dispatch({"op": "call", "name": "example", "arguments": args})
        self.assertTrue(result["tool_result"]["isError"])
        self.assertEqual(result["tool_result"]["structuredContent"], {"value": 3})
        self.session.call_tool.assert_awaited_once_with("example", args)

    async def test_call_exception_is_not_retried(self):
        self.session.call_tool.side_effect = TimeoutError("uncertain")
        with self.assertRaises(TimeoutError):
            await self.client.dispatch({"op": "call", "name": "example"})
        self.session.call_tool.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
