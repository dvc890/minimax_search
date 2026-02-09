#!/bin/bash

# Configuration - Change these or set them as environment variables
MINIMAX_API_KEY=${MINIMAX_API_KEY:-""}
SERPER_API_KEY=${SERPER_API_KEY:-""}
JINA_API_KEY=${JINA_API_KEY:-""}
PORT=${PORT:-8000}

# Check for required API keys
if [ -z "$MINIMAX_API_KEY" ]; then
    echo "Warning: MINIMAX_API_KEY is not set."
fi

# Build image if needed
echo "Building Docker image..."
docker build -t minimax-search .

# Run container
echo "Starting Minimax Search MCP Server on port $PORT..."
docker run -d \
    --name minimax-search \
    --restart unless-stopped \
    -p $PORT:8000 \
    -e MINIMAX_API_KEY="$MINIMAX_API_KEY" \
    -e SERPER_API_KEY="$SERPER_API_KEY" \
    -e JINA_API_KEY="$JINA_API_KEY" \
    minimax-search

echo "Server started!"
echo "SSE Endpoint: http://localhost:$PORT/mcp/sse"
echo "Messages Endpoint: http://localhost:$PORT/mcp/messages"
