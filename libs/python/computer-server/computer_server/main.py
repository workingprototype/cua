from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Header
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import uvicorn
import logging
import asyncio
import json
import traceback
import inspect
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from .handlers.factory import HandlerFactory
import os
import aiohttp

# Set up logging with more detail
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configure WebSocket with larger message size
WEBSOCKET_MAX_SIZE = 1024 * 1024 * 10  # 10MB limit

# Configure application with WebSocket settings
app = FastAPI(
    title="Computer API",
    description="API for the Computer project",
    version="0.1.0",
    websocket_max_size=WEBSOCKET_MAX_SIZE,
)

protocol_version = 1
try:
    import pkg_resources
    package_version = pkg_resources.get_distribution("cua-computer-server").version
except pkg_resources.DistributionNotFound:
    package_version = "unknown"

accessibility_handler, automation_handler, diorama_handler, file_handler = HandlerFactory.create_handlers()
handlers = {
    "version": lambda: {"protocol": protocol_version, "package": package_version},
    # App-Use commands
    "diorama_cmd": diorama_handler.diorama_cmd,
    # Accessibility commands
    "get_accessibility_tree": accessibility_handler.get_accessibility_tree,
    "find_element": accessibility_handler.find_element,
    # Shell commands
    "run_command": automation_handler.run_command,
    # File system commands
    "file_exists": file_handler.file_exists,
    "directory_exists": file_handler.directory_exists,
    "list_dir": file_handler.list_dir,
    "read_text": file_handler.read_text,
    "write_text": file_handler.write_text,
    "read_bytes": file_handler.read_bytes,
    "write_bytes": file_handler.write_bytes,
    "get_file_size": file_handler.get_file_size,
    "delete_file": file_handler.delete_file,
    "create_dir": file_handler.create_dir,
    "delete_dir": file_handler.delete_dir,
    # Mouse commands
    "mouse_down": automation_handler.mouse_down,
    "mouse_up": automation_handler.mouse_up,
    "left_click": automation_handler.left_click,
    "right_click": automation_handler.right_click,
    "double_click": automation_handler.double_click,
    "move_cursor": automation_handler.move_cursor,
    "drag_to": automation_handler.drag_to,
    "drag": automation_handler.drag,
    # Keyboard commands
    "key_down": automation_handler.key_down,
    "key_up": automation_handler.key_up,
    "type_text": automation_handler.type_text,
    "press_key": automation_handler.press_key,
    "hotkey": automation_handler.hotkey,
    # Scrolling actions
    "scroll": automation_handler.scroll,
    "scroll_down": automation_handler.scroll_down,
    "scroll_up": automation_handler.scroll_up,
    # Screen actions
    "screenshot": automation_handler.screenshot,
    "get_cursor_position": automation_handler.get_cursor_position,
    "get_screen_size": automation_handler.get_screen_size,
    # Clipboard actions
    "copy_to_clipboard": automation_handler.copy_to_clipboard,
    "set_clipboard": automation_handler.set_clipboard,
}


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)


manager = ConnectionManager()


@app.websocket("/ws", name="websocket_endpoint")
async def websocket_endpoint(websocket: WebSocket):
    global handlers

    # WebSocket message size is configured at the app or endpoint level, not on the instance
    await manager.connect(websocket)
    
    # Check if CONTAINER_NAME is set (indicating cloud provider)
    container_name = os.environ.get("CONTAINER_NAME")
    
    # If cloud provider, perform authentication handshake
    if container_name:
        try:
            logger.info(f"Cloud provider detected. CONTAINER_NAME: {container_name}. Waiting for authentication...")
            
            # Wait for authentication message
            auth_data = await websocket.receive_json()
            
            # Validate auth message format
            if auth_data.get("command") != "authenticate":
                await websocket.send_json({
                    "success": False,
                    "error": "First message must be authentication"
                })
                await websocket.close()
                manager.disconnect(websocket)
                return
            
            # Extract credentials
            client_api_key = auth_data.get("params", {}).get("api_key")
            client_container_name = auth_data.get("params", {}).get("container_name")
            
            # Layer 1: VM Identity Verification
            if client_container_name != container_name:
                logger.warning(f"VM name mismatch. Expected: {container_name}, Got: {client_container_name}")
                await websocket.send_json({
                    "success": False,
                    "error": "VM name mismatch"
                })
                await websocket.close()
                manager.disconnect(websocket)
                return
            
            # Layer 2: API Key Validation with TryCUA API
            if not client_api_key:
                await websocket.send_json({
                    "success": False,
                    "error": "API key required"
                })
                await websocket.close()
                manager.disconnect(websocket)
                return
            
            # Validate with TryCUA API
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Authorization": f"Bearer {client_api_key}"
                    }
                    
                    async with session.get(
                        f"https://www.trycua.com/api/vm/auth?container_name={container_name}",
                        headers=headers,
                    ) as resp:
                        if resp.status != 200:
                            error_msg = await resp.text()
                            logger.warning(f"API validation failed: {error_msg}")
                            await websocket.send_json({
                                "success": False,
                                "error": "Authentication failed"
                            })
                            await websocket.close()
                            manager.disconnect(websocket)
                            return
                        
                        # If we get a 200 response with VNC URL, the VM exists and user has access
                        vnc_url = (await resp.text()).strip()
                        if not vnc_url:
                            logger.warning(f"No VNC URL returned for VM: {container_name}")
                            await websocket.send_json({
                                "success": False,
                                "error": "VM not found"
                            })
                            await websocket.close()
                            manager.disconnect(websocket)
                            return
                        
                        logger.info(f"Authentication successful for VM: {container_name}")
                        await websocket.send_json({
                            "success": True,
                            "message": "Authenticated"
                        })
            
            except Exception as e:
                logger.error(f"Error validating with TryCUA API: {e}")
                await websocket.send_json({
                    "success": False,
                    "error": "Authentication service unavailable"
                })
                await websocket.close()
                manager.disconnect(websocket)
                return

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            await websocket.send_json({
                "success": False,
                "error": "Authentication failed"
            })
            await websocket.close()
            manager.disconnect(websocket)
            return

    try:
        while True:
            try:
                data = await websocket.receive_json()
                command = data.get("command")
                params = data.get("params", {})

                if command not in handlers:
                    await websocket.send_json(
                        {"success": False, "error": f"Unknown command: {command}"}
                    )
                    continue

                try:
                    # Filter params to only include those accepted by the handler function
                    handler_func = handlers[command]
                    sig = inspect.signature(handler_func)
                    filtered_params = {k: v for k, v in params.items() if k in sig.parameters}
                    
                    result = await handler_func(**filtered_params)
                    await websocket.send_json({"success": True, **result})
                except Exception as cmd_error:
                    logger.error(f"Error executing command {command}: {str(cmd_error)}")
                    logger.error(traceback.format_exc())
                    await websocket.send_json({"success": False, "error": str(cmd_error)})

            except WebSocketDisconnect:
                raise
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON decode error: {str(json_err)}")
                await websocket.send_json(
                    {"success": False, "error": f"Invalid JSON: {str(json_err)}"}
                )
            except Exception as loop_error:
                logger.error(f"Error in message loop: {str(loop_error)}")
                logger.error(traceback.format_exc())
                await websocket.send_json({"success": False, "error": str(loop_error)})

    except WebSocketDisconnect:
        logger.info("Client disconnected")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Fatal error in websocket connection: {str(e)}")
        logger.error(traceback.format_exc())
        try:
            await websocket.close()
        except:
            pass
        manager.disconnect(websocket)


@app.post("/cmd")
async def cmd_endpoint(
    request: Request,
    container_name: Optional[str] = Header(None, alias="X-Container-Name"),
    api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Backup endpoint for when WebSocket connections fail.
    Accepts commands via HTTP POST with streaming response.
    
    Headers:
    - X-Container-Name: Container name for cloud authentication
    - X-API-Key: API key for cloud authentication
    
    Body:
    {
        "command": "command_name",
        "params": {...}
    }
    """
    global handlers
    
    # Parse request body
    try:
        body = await request.json()
        command = body.get("command")
        params = body.get("params", {})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {str(e)}")
    
    if not command:
        raise HTTPException(status_code=400, detail="Command is required")
    
    # Check if CONTAINER_NAME is set (indicating cloud provider)
    server_container_name = os.environ.get("CONTAINER_NAME")
    
    # If cloud provider, perform authentication
    if server_container_name:
        logger.info(f"Cloud provider detected. CONTAINER_NAME: {server_container_name}. Performing authentication...")
        
        # Layer 1: VM Identity Verification
        if container_name != server_container_name:
            logger.warning(f"VM name mismatch. Expected: {server_container_name}, Got: {container_name}")
            raise HTTPException(status_code=401, detail="VM name mismatch")
        
        # Layer 2: API Key Validation with TryCUA API
        if not api_key:
            raise HTTPException(status_code=401, detail="API key required")
        
        # Validate with TryCUA API
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {api_key}"
                }
                
                async with session.get(
                    f"https://www.trycua.com/api/vm/auth?container_name={server_container_name}",
                    headers=headers,
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"API key validation failed. Status: {resp.status}")
                        raise HTTPException(status_code=401, detail="Invalid API key")
                    
                    auth_response = await resp.json()
                    if not auth_response.get("success"):
                        logger.warning(f"API key validation failed. Response: {auth_response}")
                        raise HTTPException(status_code=401, detail="Invalid API key")
                    
                    logger.info("Authentication successful")
        
        except aiohttp.ClientError as e:
            logger.error(f"Failed to validate API key with TryCUA API: {str(e)}")
            raise HTTPException(status_code=500, detail="Authentication service unavailable")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {str(e)}")
            raise HTTPException(status_code=500, detail="Authentication failed")
    
    if command not in handlers:
        raise HTTPException(status_code=400, detail=f"Unknown command: {command}")
    
    async def generate_response():
        """Generate streaming response for the command execution"""
        try:
            # Filter params to only include those accepted by the handler function
            handler_func = handlers[command]
            sig = inspect.signature(handler_func)
            filtered_params = {k: v for k, v in params.items() if k in sig.parameters}
            
            # Execute the command
            result = await handler_func(**filtered_params)
            
            # Stream the successful result
            response_data = {"success": True, **result}
            yield f"data: {json.dumps(response_data)}\n\n"
            
        except Exception as cmd_error:
            logger.error(f"Error executing command {command}: {str(cmd_error)}")
            logger.error(traceback.format_exc())
            
            # Stream the error result
            error_data = {"success": False, "error": str(cmd_error)}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-Container-Name, X-API-Key"
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
