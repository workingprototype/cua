import tempfile
import json
import time
import zipfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING
from threading import Lock
from .interface.tracing_interface import ITracingManager
import asyncio
import threading

if TYPE_CHECKING:
    from .computer import Computer


class TracingManager(ITracingManager):
    """Client-side tracing manager for recording events and attachments."""
    
    def __init__(self, computer: "Computer"):
        self.computer = computer
        self._is_tracing = False
        self.trace_dir: Optional[Path] = None
        self.events_file: Optional[Path] = None
        self.attachments_dir: Optional[Path] = None
        self._server_tracing_active = False
        self._lock = threading.Lock()
    
    @property
    def is_tracing(self) -> bool:
        """Check if tracing is currently active."""
        return self._is_tracing
        
    async def start(self, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Start a new tracing session.
        
        Args:
            options: Optional configuration dict with keys like:
                - video: bool (not implemented yet)
                - screenshots: bool (not implemented yet)
                - api_calls: bool (not implemented yet)
                - accessibility_tree: bool (not implemented yet)
                - metadata: bool (not implemented yet)
        """
        with self._lock:
            if self.is_tracing:
                return {"success": False, "error": "Tracing already in progress"}
            
            try:
                # Start server-side tracing
                server_result = await self.computer.interface.start_tracing()
                if not server_result.get("success", False):
                    return {"success": False, "error": f"Failed to start server tracing: {server_result.get('error', 'Unknown error')}"}
                
                self._server_tracing_active = True
                
                # Create temporary directory for client-side trace session
                self.trace_dir = Path(tempfile.mkdtemp(prefix="trace_client_"))
                self.events_file = self.trace_dir / "events.jsonl"
                self.attachments_dir = self.trace_dir / "attachments"
                self.attachments_dir.mkdir(exist_ok=True)
                
                # Initialize events file
                self.events_file.touch()
                
                self._is_tracing = True
                
                # Log the start event
                self.log("tracing.start", {
                    "timestamp": time.time(),
                    "client_trace_dir": str(self.trace_dir),
                    "server_trace_dir": server_result.get("trace_dir"),
                    "options": options or {}
                })
                
                return {
                    "success": True,
                    "client_trace_dir": str(self.trace_dir),
                    "server_trace_dir": server_result.get("trace_dir"),
                    "options": options or {}
                }
                
            except Exception as e:
                # Clean up if something went wrong
                if self._server_tracing_active:
                    try:
                        await self.computer.interface.stop_tracing()
                    except:
                        pass
                    self._server_tracing_active = False
                
                return {"success": False, "error": str(e)}
    
    async def stop(self, options: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Stop the current tracing session.
        
        Args:
            options: Optional dict with 'path' key for saving location
        """
        with self._lock:
            if not self.is_tracing:
                return {"success": False, "error": "No tracing session in progress"}
            
            try:
                # Log the stop event
                self.log("tracing.stop", {
                    "timestamp": time.time()
                })
                
                # Stop server-side tracing
                server_result = {}
                if self._server_tracing_active:
                    server_result = await self.computer.interface.stop_tracing()
                    self._server_tracing_active = False
                
                # Collect client-side files
                client_files = []
                if self.events_file and self.events_file.exists():
                    client_files.append(str(self.events_file))
                
                # Add all client attachment files
                if self.attachments_dir and self.attachments_dir.exists():
                    for file_path in self.attachments_dir.rglob("*"):
                        if file_path.is_file():
                            client_files.append(str(file_path))
                
                # Get server files
                server_files = server_result.get("files", [])
                
                # Merge files if save path is provided
                save_path = None
                if options and "path" in options:
                    save_path = await self._merge_and_save(client_files, server_files, options["path"])
                
                client_trace_dir = str(self.trace_dir) if self.trace_dir else None
                
                # Reset state
                self._is_tracing = False
                self.trace_dir = None
                self.events_file = None
                self.attachments_dir = None
                
                result = {
                    "success": True,
                    "client_files": client_files,
                    "server_files": server_files,
                    "client_trace_dir": client_trace_dir,
                    "server_trace_dir": server_result.get("trace_dir")
                }
                
                if save_path:
                    result["saved_to"] = save_path
                
                return result
                
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    def log(self, key: str, data: Dict[str, Any]) -> bool:
        """Log an event to the client-side events file.
        
        Args:
            key: Event key (will be prefixed with "client.")
            data: Event data dictionary
        """
        if not self.is_tracing or not self.events_file:
            return False
        
        try:
            # Prefix the key with "client"
            prefixed_key = f"client.{key}"
            
            event = {
                "timestamp": time.time(),
                "key": prefixed_key,
                "data": data
            }
            
            # Append to events file
            with open(self.events_file, "a") as f:
                f.write(json.dumps(event) + "\n")
            
            return True
            
        except Exception as e:
            print(f"Error logging event: {e}")
            return False
    
    def add_attachment(self, relpath: str, data: bytes) -> bool:
        """Add an attachment file to the client-side trace.
        
        Args:
            relpath: Relative path for the attachment
            data: Binary data to store
        """
        if not self.is_tracing or not self.attachments_dir:
            return False
        
        try:
            # Prefix the path with "client"
            prefixed_path = f"client/{relpath}"
            attachment_path = self.attachments_dir / prefixed_path
            
            # Create parent directories if needed
            attachment_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the attachment
            with open(attachment_path, "wb") as f:
                f.write(data)
            
            # Log the attachment event
            self.log("attachment.added", {
                "path": prefixed_path,
                "size": len(data)
            })
            
            return True
            
        except Exception as e:
            print(f"Error adding attachment: {e}")
            return False
    
    async def _merge_and_save(self, client_files: List[str], server_files: List[str], save_path: str) -> str:
        """Merge client and server files and save to specified path."""
        try:
            # Determine if we're saving as zip or directory
            save_path_obj = Path(save_path)
            is_zip = save_path_obj.suffix.lower() == '.zip'
            
            if is_zip:
                # Create zip file
                with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add client files
                    for file_path in client_files:
                        file_obj = Path(file_path)
                        if file_obj.exists():
                            # Determine archive path
                            if "events.jsonl" in file_path:
                                archive_path = "client_events.jsonl"
                            elif "attachments" in file_path:
                                # Keep relative path from attachments dir
                                rel_path = file_obj.relative_to(file_obj.parent.parent)
                                archive_path = str(rel_path)
                            else:
                                archive_path = file_obj.name
                            
                            zipf.write(file_path, archive_path)
                    
                    # Add server files by reading them through the interface
                    for file_path in server_files:
                        try:
                            # Read server file content
                            if "events.jsonl" in file_path:
                                content = await self.computer.interface.read_text(file_path)
                                zipf.writestr("server_events.jsonl", content.encode())
                            else:
                                # For attachments, read as bytes
                                content = await self.computer.interface.read_bytes(file_path)
                                # Determine archive path
                                server_path = Path(file_path)
                                if "attachments" in file_path:
                                    # Extract relative path from server attachments
                                    parts = server_path.parts
                                    if "attachments" in parts:
                                        idx = parts.index("attachments")
                                        rel_path = "/".join(parts[idx:])
                                        archive_path = f"server_{rel_path}"
                                    else:
                                        archive_path = f"server_{server_path.name}"
                                else:
                                    archive_path = f"server_{server_path.name}"
                                
                                zipf.writestr(archive_path, content)
                        except Exception as e:
                            print(f"Warning: Could not read server file {file_path}: {e}")
                            continue
            
            else:
                # Create directory structure
                save_path_obj.mkdir(parents=True, exist_ok=True)
                
                # Copy client files
                client_dir = save_path_obj / "client"
                client_dir.mkdir(exist_ok=True)
                
                for file_path in client_files:
                    file_obj = Path(file_path)
                    if file_obj.exists():
                        if "events.jsonl" in file_path:
                            shutil.copy2(file_path, client_dir / "events.jsonl")
                        elif "attachments" in file_path:
                            # Recreate directory structure
                            rel_path = file_obj.relative_to(file_obj.parent.parent)
                            dest_path = client_dir / rel_path
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(file_path, dest_path)
                
                # Copy server files
                server_dir = save_path_obj / "server"
                server_dir.mkdir(exist_ok=True)
                
                for file_path in server_files:
                    try:
                        server_path = Path(file_path)
                        if "events.jsonl" in file_path:
                            content = await self.computer.interface.read_text(file_path)
                            with open(server_dir / "events.jsonl", "w") as f:
                                f.write(content)
                        else:
                            # For attachments
                            content = await self.computer.interface.read_bytes(file_path)
                            if "attachments" in file_path:
                                parts = server_path.parts
                                if "attachments" in parts:
                                    idx = parts.index("attachments")
                                    rel_path = Path(*parts[idx:])
                                    dest_path = server_dir / rel_path
                                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                                    with open(dest_path, "wb") as f:
                                        f.write(content)
                    except Exception as e:
                        print(f"Warning: Could not copy server file {file_path}: {e}")
                        continue
            
            return save_path
            
        except Exception as e:
            raise Exception(f"Failed to merge and save trace files: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current tracing status."""
        return {
            "is_tracing": self.is_tracing,
            "client_trace_dir": str(self.trace_dir) if self.trace_dir else None,
            "server_tracing_active": self._server_tracing_active
        }
