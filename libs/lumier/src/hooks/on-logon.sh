#!/bin/bash

# Arguments passed from execute_remote_script in vm.sh
# $1: VNC_PASSWORD
# $2: HOST_SHARED_PATH (Path inside VM where host shared dir is mounted, e.g., /Volumes/My Shared Files)

VNC_PASSWORD="$1"
HOST_SHARED_PATH="$2"

# Define the path to the user's optional on-logon script within the shared folder
USER_ON_LOGON_SCRIPT_PATH="$HOST_SHARED_PATH/lifecycle/on-logon.sh"

# Set default value for VNC_DEBUG if not provided
VNC_DEBUG=${VNC_DEBUG:-0}

# Only show debug logs if VNC_DEBUG is enabled
if [ "$VNC_DEBUG" = "1" ]; then
    echo "[Remote] Lumier entry point script starting..."
    echo "[Remote] Checking for user script at: $USER_ON_LOGON_SCRIPT_PATH"
fi

# Check if the user-provided script exists
if [ -f "$USER_ON_LOGON_SCRIPT_PATH" ]; then
    # Only show debug logs if VNC_DEBUG is enabled
    if [ "$VNC_DEBUG" = "1" ]; then
        echo "[Remote] Found user script. Making executable and running..."
    fi
    
    chmod +x "$USER_ON_LOGON_SCRIPT_PATH"

    # Execute the user script in a subshell, passing VNC password and shared path as arguments
    "$USER_ON_LOGON_SCRIPT_PATH" "$VNC_PASSWORD" "$HOST_SHARED_PATH"

    # Capture exit code (optional, but good practice)
    USER_SCRIPT_EXIT_CODE=$?
    
    # Only show debug logs if VNC_DEBUG is enabled
    if [ "$VNC_DEBUG" = "1" ]; then
        echo "[Remote] User script finished with exit code: $USER_SCRIPT_EXIT_CODE."
    fi

    # Propagate the exit code if non-zero (optional)
    # if [ $USER_SCRIPT_EXIT_CODE -ne 0 ]; then
    #     exit $USER_SCRIPT_EXIT_CODE
    # fi
else
    # Only show debug logs if VNC_DEBUG is enabled
    if [ "$VNC_DEBUG" = "1" ]; then
        echo "[Remote] No user-provided on-logon script found at $USER_ON_LOGON_SCRIPT_PATH. Skipping."
    fi
fi

# Only show debug logs if VNC_DEBUG is enabled
if [ "$VNC_DEBUG" = "1" ]; then
    echo "[Remote] Lumier entry point script finished."
fi
exit 0 # Ensure the entry point script exits cleanly if no user script or user script succeeded
