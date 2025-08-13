FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies including virtual display and desktop environment
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
    x11vnc \
    fluxbox \
    xterm \
    firefox-esr \
    gnome-screenshot \
    websockify \
    git \
    fonts-liberation \
    fonts-dejavu \
    xfonts-base \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy computer-server files
COPY . /app/

# Install Python dependencies
RUN pip install -e .

# Download and setup noVNC for web-based VNC access
RUN git clone https://github.com/novnc/noVNC.git /opt/noVNC && \
    git clone https://github.com/novnc/websockify.git /opt/noVNC/utils/websockify

# Create a custom index page to avoid hostname issues
RUN echo '<!DOCTYPE html>\n\
<html>\n\
<head>\n\
    <title>CUA Desktop Viewer</title>\n\
    <meta charset="utf-8">\n\
</head>\n\
<body>\n\
    <h1>CUA Desktop Automation Viewer</h1>\n\
    <p>Click the link below to view the desktop automation in real-time:</p>\n\
    <a href="/vnc.html?host=localhost&port=6080&autoconnect=true&resize=scale" \n\
       style="font-size: 18px; color: blue; text-decoration: none; border: 2px solid blue; padding: 10px; display: inline-block;">🖥️ View Desktop Automation</a>\n\
    <br><br>\n\
    <p><strong>Instructions:</strong></p>\n\
    <ul>\n\
        <li>Click the link above to connect to the desktop</li>\n\
        <li>You should see a desktop with Fluxbox window manager</li>\n\
        <li>Watch as CUA agents control the desktop automatically!</li>\n\
    </ul>\n\
</body>\n\
</html>' > /opt/noVNC/index.html

# Expose port
EXPOSE 8081

# Set up X11 environment for GUI apps
ENV DISPLAY=:99
ENV QT_X11_NO_MITSHM=1

# Create startup script for virtual display with desktop
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
echo "X server started successfully"\n\
# Set up fonts and environment\n\
export DISPLAY=:99\n\
export LANG=C.UTF-8\n\
# Start window manager\n\
fluxbox -display :99 &\n\
sleep 2\n\
# Start a simple application to make desktop visible\n\
xterm -geometry 80x24+100+100 &\n\
# Start VNC server for remote viewing\n\
x11vnc -display :99 -nopw -listen localhost -xkb -forever -shared -bg\n\
echo "VNC server started on localhost:5900"\n\
# Start noVNC web server\n\
cd /opt/noVNC && ./utils/novnc_proxy --vnc localhost:5900 --listen 0.0.0.0:6080 &\n\
echo "noVNC web server started on port 6080"\n\
echo "Access via: http://localhost:6080/vnc.html?host=localhost&port=6080"\n\
# Start the computer server\n\
python -m computer_server --host 0.0.0.0 --port 8081\n' > /app/start.sh && \
    chmod +x /app/start.sh

# Command to run the server with virtual display
CMD ["/app/start.sh"]