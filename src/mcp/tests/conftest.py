"""Load the MCP SDK and isolate SDK first-run settings for child fixtures."""
import os

import mcp.client  # noqa: F401

os.environ["DOTNET_ADD_GLOBAL_TOOLS_TO_PATH"] = "false"
os.environ["DOTNET_GENERATE_ASPNET_CERTIFICATE"] = "false"
