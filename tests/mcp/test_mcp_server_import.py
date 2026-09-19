"""MCP server import smoke test.

`uv tool install` can resolve `mcp>=1.6.0` to 2.x, which dropped the v1
low-level types this package still uses. Importing the routes module is the
same failure users hit at kash startup.
"""

from __future__ import annotations


def test_mcp_server_routes_import():
    from mcp.server.lowlevel.server import StructuredContent, UnstructuredContent

    from kash.mcp.mcp_server_routes import create_base_server

    assert StructuredContent is not None
    assert UnstructuredContent is not None
    app = create_base_server()
    assert app.name == "kash-mcp-server"
