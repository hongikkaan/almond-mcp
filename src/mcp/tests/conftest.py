"""Load the MCP SDK before pytest can alias the flat source tree as `mcp`."""
import mcp.client  # noqa: F401
