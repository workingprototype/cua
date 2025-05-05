#!/usr/bin/env bash

start_vm() {
    # Determine storage path for VM
    STORAGE_PATH="$HOST_STORAGE_PATH"
    if [ -z "$STORAGE_PATH" ]; then
        STORAGE_PATH="storage_${VM_NAME}"
    fi

    # Check if VM exists and its status using JSON format
    VM_INFO=$(lume_get "$VM_NAME" "$STORAGE_PATH")
    echo "VM_INFO: $VM_INFO"

    # Check if VM not found error
    if [[ $VM_INFO == *"Virtual machine not found"* ]]; then
        IMAGE_NAME="${VERSION##*/}"
        # Parse registry and organization from VERSION
        REGISTRY=$(echo $VERSION | cut -d'/' -f1)
        ORGANIZATION=$(echo $VERSION | cut -d'/' -f2)
        
        echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] INFO: Pulling VM image $IMAGE_NAME from $REGISTRY/$ORGANIZATION to $STORAGE_PATH"
        lume_pull "$IMAGE_NAME" "$VM_NAME" "$STORAGE_PATH" "$REGISTRY" "$ORGANIZATION"
    else
        # Parse the JSON status - check if it contains "status" : "running"
        if [[ $VM_INFO == *'"status" : "running"'* ]]; then
            lume_stop "$VM_NAME" "$STORAGE_PATH"
        fi
    fi

    # Format memory size for display purposes
    MEMORY_DISPLAY="$RAM_SIZE"
    if [[ ! "$RAM_SIZE" == *"GB"* && ! "$RAM_SIZE" == *"MB"* ]]; then
        MEMORY_DISPLAY="${RAM_SIZE}MB"
    fi
    
    # Set VM parameters using the new wrapper function
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] INFO: Updating VM settings cpu=$CPU_CORES name=$VM_NAME location=$STORAGE_PATH display=$DISPLAY memory=$MEMORY_DISPLAY disk_size=unchanged"
    lume_set "$VM_NAME" "$STORAGE_PATH" "$CPU_CORES" "$RAM_SIZE" "$DISPLAY"

    # Fetch VM configuration
    CONFIG_JSON=$(lume_get "$VM_NAME" "$STORAGE_PATH")
    
    # Setup shared directory args if necessary
    SHARED_DIR_ARGS=""
    if [ -d "/shared" ]; then
        if [ -n "$HOST_SHARED_PATH" ]; then
            SHARED_DIR_ARGS="--shared-dir=$HOST_SHARED_PATH"
        else
            echo "Warning: /shared volume exists but HOST_SHARED_PATH is not set. Cannot mount volume."
        fi
    fi

    # Run VM with VNC and shared directory using curl
    lume_run $SHARED_DIR_ARGS --storage "$STORAGE_PATH" "$VM_NAME" &
    # lume run "$VM_NAME" --storage "$STORAGE_PATH" --no-display

    # Wait for VM to be running and VNC URL to be available
    vm_ip=""
    vnc_url=""
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        # Get VM info as JSON using the API function
        VM_INFO=$(lume_get "$VM_NAME" "$STORAGE_PATH")
        # VM_INFO=$(lume get "$VM_NAME" --storage "$STORAGE_PATH" -f json 2>/dev/null)
        
        # Check if VM has status 'running'
        if [[ $VM_INFO == *'"status" : "running"'* ]]; then
            # Extract IP address using the existing function from utils.sh
            vm_ip=$(extract_json_field "ipAddress" "$VM_INFO")
            # Extract VNC URL using the existing function from utils.sh
            vnc_url=$(extract_json_field "vncUrl" "$VM_INFO")
            
            # If we have both IP and VNC URL, break the loop
            if [ -n "$vm_ip" ] && [ -n "$vnc_url" ]; then
                break
            fi
        fi
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ -z "$vm_ip" ] || [ -z "$vnc_url" ]; then
        echo "Timed out waiting for VM to start or VNC URL to become available."
        lume_stop "$VM_NAME" "$STORAGE_PATH" > /dev/null 2>&1
        # lume stop "$VM_NAME" --storage "$STORAGE_PATH" > /dev/null 2>&1
        exit 1
    fi

    # Parse VNC URL to extract password and port
    VNC_PASSWORD=$(echo "$vnc_url" | sed -n 's/.*:\(.*\)@.*/\1/p')
    VNC_PORT=$(echo "$vnc_url" | sed -n 's/.*:\([0-9]\+\)$/\1/p')
    
    # Wait for SSH to become available
    wait_for_ssh "$vm_ip" "$HOST_USER" "$HOST_PASSWORD" 5 20

    # Export VNC variables for entry.sh to use
    export VNC_PORT
    export VNC_PASSWORD
    
    # Execute on-logon.sh if present
    on_logon_script="/run/lifecycle/on-logon.sh"
    # Use HOST_SHARED_PATH which is set earlier in the script
    echo "Executing on-logon.sh on VM..."
    execute_remote_script "$vm_ip" "$HOST_USER" "$HOST_PASSWORD" "$on_logon_script" "$VNC_PASSWORD" "$HOST_SHARED_PATH"
}

# Get VM information using curl
lume_get() {
    local vm_name="$1"
    local storage="$2"
    local format="${3:-json}"
    local debug="${4:-false}"
    
    local api_host="${LUME_API_HOST:-host.docker.internal}"
    local api_port="${LUME_API_PORT:-3000}"
    
    # URL encode the storage path for the query parameter
    # Replace special characters with their URL encoded equivalents
    local encoded_storage=$(echo "$storage" | sed 's/\//%2F/g' | sed 's/ /%20/g' | sed 's/:/%3A/g')
    
    # Construct API URL with encoded storage parameter
    local api_url="http://${api_host}:${api_port}/lume/vms/${vm_name}?storage=${encoded_storage}"
    
    # Construct the full curl command
    local curl_cmd="curl --connect-timeout 6000 --max-time 5000 -s '$api_url'"
    
    # Print debug info
    if [[ "$debug" == "true" || "$LUMIER_DEBUG" == "1" ]]; then
        echo "[DEBUG] Calling API: $api_url"
        echo "[DEBUG] Full curl command: $curl_cmd"
    fi
    
    # Always log the curl command before sending
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] INFO: Executing curl request: $api_url"
    
    # Make the API call
    local response=$(curl --connect-timeout 6000 \
      --max-time 5000 \
      -s \
      "$api_url")
    
    # Print the response if debugging is enabled
    if [[ "$debug" == "true" || "$LUMIER_DEBUG" == "1" ]]; then
        echo "[DEBUG] API Response:"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    fi
    
    # Output the response
    echo "$response"
}

# Set VM properties using curl
lume_set() {
    local vm_name="$1"
    local storage="$2"
    local cpu="${3:-4}"
    local memory="${4:-8192}"
    local display="${5:-1024x768}"
    
    local api_host="${LUME_API_HOST:-host.docker.internal}"
    local api_port="${LUME_API_PORT:-3000}"
    
    # Handle memory format for the API
    if [[ "$memory" == *"GB"* ]]; then
        # Already in GB format, keep as is
        :  # No-op
    elif [[ "$memory" =~ ^[0-9]+$ ]]; then
        # If memory is a simple number, assume MB and convert to GB
        memory="$(awk "BEGIN { printf \"%.1f\", $memory/1024 }")GB"
    fi
    
    echo "[DEBUG] Formatted memory value: $memory"
    
    curl --connect-timeout 6000 \
      --max-time 5000 \
      -s \
      -X PATCH \
      -H "Content-Type: application/json" \
      -d "{
        \"cpu\": $cpu,
        \"memory\": \"$memory\",
        \"display\": \"$display\",
        \"storage\": \"$storage\"
      }" \
      "http://${api_host}:${api_port}/lume/vms/${vm_name}"
}

stop_vm() {
    echo "Stopping VM '$VM_NAME'..."
    STORAGE_PATH="$HOST_STORAGE_PATH"
    # Check if the VM exists and is running
    echo "STORAGE_PATH: $STORAGE_PATH"
    VM_INFO=$(lume_get "$VM_NAME" "$STORAGE_PATH")
    if [[ -z "$VM_INFO" || $VM_INFO == *"Virtual machine not found"* ]]; then
        echo "VM '$VM_NAME' does not exist."
    elif [[ $VM_INFO == *'"status" : "running"'* ]]; then
        lume_stop "$VM_NAME" "$STORAGE_PATH"
        echo "VM '$VM_NAME' was running and is now stopped."
    elif [[ $VM_INFO == *'"status" : "stopped"'* ]]; then
        echo "VM '$VM_NAME' is already stopped."
    else
        echo "Unknown VM status for '$VM_NAME'."
    fi
}

is_vm_running() {
    # Check VM status using the API function
    local vm_info
    vm_info=$(lume_get "$VM_NAME" "$HOST_STORAGE_PATH")
    if [[ $vm_info == *'"status" : "running"'* ]]; then
        return 0 # Running
    else
        return 1 # Not running or doesn't exist
    fi
    # lume ls | grep -q "$VM_NAME" # Old CLI check
}

# Stop VM with storage location specified using curl
lume_stop() {
    local vm_name="$1"
    local storage="$2"
    curl --connect-timeout 6000 \
      --max-time 5000 \
      -X POST \
      -H "Content-Type: application/json" \
      -d '{"storage":"'$storage'"}' \
      "http://host.docker.internal:3000/lume/vms/${vm_name}/stop"
}

# Pull a VM image using curl
lume_pull() {
    local image="$1"      # Image name with tag
    local vm_name="$2"    # Name for the new VM
    local storage="$3"    # Storage location
    local registry="${4:-ghcr.io}"  # Registry, default is ghcr.io
    local organization="${5:-trycua}" # Organization, default is trycua
    
    local api_host="${LUME_API_HOST:-host.docker.internal}"
    local api_port="${LUME_API_PORT:-3000}"
    
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] INFO: Pulling image $image from $registry/$organization to $storage"
    
    # Pull image via API
    curl --connect-timeout 6000 \
      --max-time 5000 \
      -s \
      -X POST \
      -H "Content-Type: application/json" \
      -d "{
        \"image\": \"$image\",
        \"name\": \"$vm_name\",
        \"registry\": \"$registry\",
        \"organization\": \"$organization\",
        \"storage\": \"$storage\"
      }" \
      "http://${api_host}:${api_port}/lume/pull"
}


# Run VM with VNC client started and shared directory using curl
lume_run() {
    # Parse args
    local shared_dir=""
    local storage="ssd"
    local vm_name="lume_vm"
    local no_display=true
    while [[ $# -gt 0 ]]; do
        case $1 in
            --shared-dir=*)
                shared_dir="${1#*=}"
                shift
                ;;
            --storage)
                storage="$2"
                shift 2
                ;;
            --no-display)
                no_display=true
                shift
                ;;
            *)
                # Assume last arg is VM name if not an option
                vm_name="$1"
                shift
                ;;
        esac
    done
    
    # Default to ~/Projects if not provided
    if [[ -z "$shared_dir" ]]; then
        shared_dir="~/Projects"
    fi
    
    local json_body="{\"noDisplay\": true, \"sharedDirectories\": [{\"hostPath\": \"$shared_dir\", \"readOnly\": false}], \"storage\": \"$storage\", \"recoveryMode\": false}"
    local curl_cmd="curl --connect-timeout 6000 \
      --max-time 5000 \
      -X POST \
      -H 'Content-Type: application/json' \
      -d '$json_body' \
      http://host.docker.internal:3000/lume/vms/$vm_name/run"
    eval "$curl_cmd"
}