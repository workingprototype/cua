FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH="/app/libs/python/core:/app/libs/python/computer:/app/libs/python/agent:/app/libs/python/som:/app/libs/python/pylume:/app/libs/python/computer-server:/app/libs/python/mcp-server"

# Install system dependencies for all platforms
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libglx-mesa0 \
    libgl1 \
    libglib2.0-0 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    cmake \
    pkg-config \
    curl \
    iputils-ping \
    net-tools \
    sed \
    xxd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the entire project temporarily
# We'll mount the real source code over this at runtime
COPY . /app/

# Create a simple .env.local file for build.sh
RUN echo "PYTHON_BIN=python" > /app/.env.local

# Modify build.sh to skip virtual environment creation
RUN sed -i 's/python -m venv .venv/echo "Skipping venv creation in Docker"/' /app/scripts/build.sh && \
    sed -i 's/source .venv\/bin\/activate/echo "Skipping venv activation in Docker"/' /app/scripts/build.sh && \
    sed -i 's/find . -type d -name ".venv" -exec rm -rf {} +/echo "Skipping .venv removal in Docker"/' /app/scripts/build.sh && \
    chmod +x /app/scripts/build.sh

# Install CUA dependencies for the real server
RUN pip install --no-cache-dir cua-computer litellm pillow

# Run the build script to install dependencies
RUN cd /app && ./scripts/build.sh

# Clean up the source files now that dependencies are installed
# When we run the container, we'll mount the actual source code
RUN rm -rf /app/* /app/.??*

# Note: This Docker image doesn't contain the lume executable (macOS-specific)
# Instead, it relies on connecting to a lume server running on the host machine
# via host.docker.internal:7777

# Default command
CMD ["bash"] 