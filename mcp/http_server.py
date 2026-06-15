"""Hosted (remote) AKC MCP — Streamable HTTP transport for deployment on AgentBase.

Reuses the akc_* tools from server.py and serves them over HTTP at /mcp, plus
/health and /invocations stubs so the AgentBase runtime probes pass.

Local run:  AKC_ENDPOINT=https://... python mcp/http_server.py
Container:  CMD python http_server.py  (server.py + this file copied flat to /app)
"""
import server  # registers `mcp` (FastMCP) + the akc_* tools at import
import uvicorn
from starlette.responses import JSONResponse
from starlette.routing import Route

mcp = server.mcp


async def health(_request):
    return JSONResponse({"status": "ok", "service": "akc-mcp"})


async def invocations(_request):
    return JSONResponse({
        "service": "akc-mcp",
        "transport": "streamable-http",
        "mcp_endpoint": "/mcp",
        "tools": ["akc_recall", "akc_remember", "akc_stats",
                  "akc_export", "akc_health", "akc_patterns", "akc_gaps"],
    })


# streamable_http_app() carries the MCP session-manager lifespan; append our
# probe routes to it rather than mounting (mounting would drop the lifespan).
app = mcp.streamable_http_app()
app.router.routes.append(Route("/health", health, methods=["GET"]))
app.router.routes.append(Route("/invocations", invocations, methods=["GET", "POST"]))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
