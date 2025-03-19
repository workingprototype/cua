#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print with color
print_info() {
    echo -e "${BLUE}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}==> $1${NC}"
}

print_error() {
    echo -e "${RED}==> $1${NC}"
}

# Docker image name
IMAGE_NAME="cua-dev-image"
CONTAINER_NAME="cua-dev-container"
PLATFORM="linux/arm64"

# Environment variables
PYTHONPATH="/app/libs/core:/app/libs/computer:/app/libs/agent:/app/libs/som:/app/libs/pylume:/app/libs/computer-server"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Command options
case "$1" in
    build)
        print_info "Building the development Docker image..."
        print_info "This will install all dependencies but won't include source code"
        docker build -f Dockerfile --platform=${PLATFORM} -t ${IMAGE_NAME} .
        print_success "Development Docker image built successfully!"
        ;;
    
    run)
        # Check for interactive flag
        if [ "$2" == "--interactive" ]; then
            print_info "Running the development Docker container with interactive shell..."
            print_info "Mounting source code from host"
            print_info "Connecting to host.docker.internal:3000"
            
            docker run -it --rm \
                --platform=${PLATFORM} \
                --name ${CONTAINER_NAME} \
                -v "$(pwd):/app" \
                -e PYTHONPATH=${PYTHONPATH} \
                -e DISPLAY=${DISPLAY:-:0} \
                -e PYLUME_HOST="host.docker.internal" \
                ${IMAGE_NAME} bash
        else
            # Run the specified example
            if [ -z "$2" ]; then
                print_error "Please specify an example file, e.g., ./run-docker-dev.sh run computer_examples.py"
                exit 1
            fi
            print_info "Running example: $2"
            print_info "Connecting to host.docker.internal:3000"
            
            docker run -it --rm \
                --platform=${PLATFORM} \
                --name ${CONTAINER_NAME} \
                -v "$(pwd):/app" \
                -e PYTHONPATH=${PYTHONPATH} \
                -e DISPLAY=${DISPLAY:-:0} \
                -e PYLUME_HOST="host.docker.internal" \
                ${IMAGE_NAME} python "/app/examples/$2"
        fi
        ;;
    
    stop)
        print_info "Stopping any running containers..."
        docker stop ${CONTAINER_NAME} 2>/dev/null || true
        print_success "Done!"
        ;;
        
    *)
        echo "Usage: $0 {build|run [--interactive] [filename]|stop}"
        echo ""
        echo "Commands:"
        echo "  build                      Build the development Docker image with dependencies"
        echo "  run [example_filename]     Run the specified example file in the container"
        echo "  run --interactive          Run the container with mounted code and get an interactive shell"
        echo "  stop                       Stop the container"
        exit 1
esac

exit 0 