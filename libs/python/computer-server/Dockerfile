FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies including virtual display
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglx-mesa0 \
    libgl1 \
    libglib2.0-0 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    xvfb \
    x11-utils \
    x11-xserver-utils \
    dbus \
    dbus-x11 \
    python3-tk \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy computer-server files
COPY . /app/

# Install Python dependencies
RUN pip install -e .

# Expose port
EXPOSE 8081

# Set up X11 environment for GUI apps
ENV DISPLAY=:99
ENV QT_X11_NO_MITSHM=1

# Create startup script for virtual display
RUN echo '#!/bin/bash\n\
# Clean up any existing X lock files\n\
rm -f /tmp/.X*-lock\n\
# Start virtual display with error handling\n\
Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset &\n\
XVFB_PID=$!\n\
export DISPLAY=:99\n\
# Wait for X server to be ready\n\
timeout=10\n\
while [ $timeout -gt 0 ]; do\n\
    if xdpyinfo -display :99 >/dev/null 2>&1; then\n\
        break\n\
    fi\n\
    sleep 1\n\
    timeout=$((timeout-1))\n\
done\n\
# Start the computer server\n\
python -m computer_server --host 0.0.0.0 --port 8081\n' > /app/start.sh && \
    chmod +x /app/start.sh

# Command to run the server with virtual display
CMD ["/app/start.sh"]