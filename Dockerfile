
FROM python:3.10-slim

WORKDIR /app

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY server.py server_sse.py minimax_search_browse.py ./

# Install dependencies including the project itself in editable mode or just dependencies
# Since we have pyproject.toml, pip install . should work to install dependencies defined therein
RUN pip install --no-cache-dir .

# Expose port
EXPOSE 8000

# Run the server
CMD ["uvicorn", "server_sse:app", "--host", "0.0.0.0", "--port", "8000"]
