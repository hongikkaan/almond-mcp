"""The public Sheet database registry is retired, independent of native layouts."""
import asyncio
from fastmcp import Client, FastMCP
from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.drawings.tools import register


def test_sheet_registry_is_not_exposed_or_exported():
    mcp = FastMCP('drawings-without-registry')
    exports = register(mcp, FeatureContext({}))
    async def verify():
        async with Client(mcp) as client:
            names = {tool.name for tool in await client.list_tools()}
            assert names == set(exports) == {'list_drawing_recipes', 'get_drawing_recipe', 'apply_drawing_style', 'import_drawing_hatch_patterns'}
            assert not any('sheet' in name for name in names)
    asyncio.run(verify())
