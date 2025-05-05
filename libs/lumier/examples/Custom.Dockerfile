# Custom Lumier image that uses the base lumier:latest image
# and overrides environment variables as needed
FROM trycua/lumier:latest

# Default environment variables that can be overridden at build time
# These values will override the defaults from the base image
ARG CUSTOM_VERSION="ghcr.io/trycua/macos-sequoia-vanilla:latest"
ARG CUSTOM_RAM_SIZE="16384"
ARG CUSTOM_CPU_CORES="8"
ARG CUSTOM_DISK_SIZE="100"
ARG CUSTOM_DISPLAY="1024x768"
ARG CUSTOM_VM_NAME="custom-vanilla-lumier"

# Set environment variables based on build args
ENV VERSION=${CUSTOM_VERSION}
ENV RAM_SIZE=${CUSTOM_RAM_SIZE}
ENV CPU_CORES=${CUSTOM_CPU_CORES}
ENV DISK_SIZE=${CUSTOM_DISK_SIZE}
ENV DISPLAY=${CUSTOM_DISPLAY}
ENV VM_NAME=${CUSTOM_VM_NAME}

# Create the necessary directory for lifecycle scripts
RUN mkdir -p /run/lifecycle

# Copy custom on-logon script to be executed inside the VM after login
COPY src/lifecycle/on-logon.sh /run/lifecycle/on-logon.sh

# Make sure the script is executable
RUN chmod +x /run/lifecycle/on-logon.sh

# We're using the default entrypoint from the base image
