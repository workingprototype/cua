import os
import json
import time
import tempfile
import shutil
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
import threading


class ServerTracingManager:
    """Server-side tracing manager for recording events and attachments."""
    
    def __init__(self, namespace: str = "server"):
        self.namespace = namespace
        self.is_tracing = False
        self.trace_dir: Optional[Path] = None
        self.events_file: Optional[Path] = None
        self.attachments_dir: Optional[Path] = None
        self._lock = threading.Lock()
        
    def start_tracing(self) -> Dict[str, Any]:
        """Start a new tracing session."""
        with self._lock:
            if self.is_tracing:
                return {"success": False, "error": "Tracing already in progress"}
            
            try:
                # Create temporary directory for this trace session
                self.trace_dir = Path(tempfile.mkdtemp(prefix=f"trace_{self.namespace}_"))
                self.events_file = self.trace_dir / "events.jsonl"
                self.attachments_dir = self.trace_dir / "attachments"
                self.attachments_dir.mkdir(exist_ok=True)
                
                # Initialize events file
                self.events_file.touch()
                
                self.is_tracing = True
                
                # Log the start event
                self.log_event("tracing.start", {
                    "timestamp": time.time(),
                    "namespace": self.namespace,
                    "trace_dir": str(self.trace_dir)
                })
                
                return {
                    "success": True,
                    "trace_dir": str(self.trace_dir),
                    "namespace": self.namespace
                }
                
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    def stop_tracing(self) -> Dict[str, Any]:
        """Stop the current tracing session and return file paths."""
        with self._lock:
            if not self.is_tracing:
                return {"success": False, "error": "No tracing session in progress"}
            
            try:
                # Log the stop event
                self.log_event("tracing.stop", {
                    "timestamp": time.time(),
                    "namespace": self.namespace
                })
                
                # Collect all files
                files = []
                if self.events_file and self.events_file.exists():
                    files.append(str(self.events_file))
                
                # Add all attachment files
                if self.attachments_dir and self.attachments_dir.exists():
                    for file_path in self.attachments_dir.rglob("*"):
                        if file_path.is_file():
                            files.append(str(file_path))
                
                trace_dir = str(self.trace_dir) if self.trace_dir else None
                
                # Reset state
                self.is_tracing = False
                self.trace_dir = None
                self.events_file = None
                self.attachments_dir = None
                
                return {
                    "success": True,
                    "files": files,
                    "trace_dir": trace_dir,
                    "namespace": self.namespace
                }
                
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    def log_event(self, key: str, data: Dict[str, Any]) -> bool:
        """Log an event to the events file."""
        if not self.is_tracing or not self.events_file:
            return False
        
        try:
            # Prefix the key with namespace
            prefixed_key = f"{self.namespace}.{key}"
            
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
        """Add an attachment file to the trace."""
        if not self.is_tracing or not self.attachments_dir:
            return False
        
        try:
            # Prefix the path with namespace
            prefixed_path = f"{self.namespace}/{relpath}"
            attachment_path = self.attachments_dir / prefixed_path
            
            # Create parent directories if needed
            attachment_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the attachment
            with open(attachment_path, "wb") as f:
                f.write(data)
            
            # Log the attachment event
            self.log_event("attachment.added", {
                "path": prefixed_path,
                "size": len(data)
            })
            
            return True
            
        except Exception as e:
            print(f"Error adding attachment: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current tracing status."""
        return {
            "is_tracing": self.is_tracing,
            "namespace": self.namespace,
            "trace_dir": str(self.trace_dir) if self.trace_dir else None
        }


# Global tracing manager instance
_tracing_manager = ServerTracingManager(namespace="server")


def get_tracing_manager() -> ServerTracingManager:
    """Get the global server tracing manager instance."""
    return _tracing_manager
