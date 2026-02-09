
import os
import sys
import logging
import asyncio
import uuid
from typing import Dict, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("minimax_search_sse")

# Import dependencies
try:
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse, Response
    from starlette.requests import Request
    from sse_starlette.sse import EventSourceResponse
    from mcp.server.sse import SseServerTransport
    from mcp.server import Server
    from mcp.types import JSONRPCMessage
except ImportError as e:
    logger.error(f"Missing dependencies: {e}")
    sys.exit(1)

# Add project root directory to path
sys.path.append(os.path.dirname(__file__))

# Import the existing server implementation
try:
    from server import MinimaxSearchMCPServer
except ImportError:
    logger.error("Could not import MinimaxSearchMCPServer from server.py")
    sys.exit(1)


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, SseServerTransport] = {}

    async def create_session(self, request: Request):
        session_id = str(uuid.uuid4())
        # The client will be told to POST messages to this endpoint
        # We include the session_id as a query parameter
        endpoint = f"/messages?session_id={session_id}"
        
        transport = SseServerTransport(endpoint)
        self.sessions[session_id] = transport
        
        # Create a new server instance for this session (if needed)
        # Assuming one server instance handles request logic statelessly or we create per session
        # MinimaxSearchMCPServer seems stateless in terms of "app" structure, but run() manages connection state
        # So we should probably use the same server app definition but run() creates new connection context
        # But wait, mcp_server.run() takes streams. It doesn't instantiate new "Server" logic per se?
        # Actually server.app is the Server instance. run() is a method on it.
        # run() handles one connection. So we can reuse the same server instance for multiple run() calls? 
        # Yes, standard MCP servers are designed to handle multiple connections via separate run() calls.
        
        mcp_server = MinimaxSearchMCPServer().app
        
        async def run_server(read_stream, write_stream):
            try:
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options()
                )
            except Exception as e:
                logger.error(f"Session {session_id} error: {e}", exc_info=True)
            finally:
                # Cleanup session on disconnect
                if session_id in self.sessions:
                    del self.sessions[session_id]
                    logger.info(f"Session {session_id} closed")

        # Connect transport -> get streams
        read_stream, write_stream = await transport.connect()
        
        # Start server loop
        asyncio.create_task(run_server(read_stream, write_stream))
        
        # Handle the SSE request
        return await transport.handle_sse(request)

    async def handle_message(self, request: Request):
        session_id = request.query_params.get("session_id")
        
        if not session_id or session_id not in self.sessions:
            return JSONResponse({"error": "Session not found or invalid session_id"}, status_code=404)
        
        transport = self.sessions[session_id]
        try:
            await transport.handle_post_message(request)
            return Response(status_code=200)
        except Exception as e:
            logger.error(f"Error handling message for session {session_id}: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

session_manager = SessionManager()

async def sse_endpoint(request: Request):
    return await session_manager.create_session(request)

async def messages_endpoint(request: Request):
    return await session_manager.handle_message(request)

routes = [
    Route("/sse", sse_endpoint, methods=["GET"]),
    Route("/mcp", sse_endpoint, methods=["GET"]),      # Alias for /sse
    Route("/mcp/sse", sse_endpoint, methods=["GET"]),  # Alias for /sse
    Route("/messages", messages_endpoint, methods=["POST"]),
    # Handle /mcp/messages as well just in case, though we tell client /messages
    Route("/mcp/messages", messages_endpoint, methods=["POST"]), 
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
