"""
Safari-specific getter functions for extracting data from Safari browser.

This file is AI-generated based on the PyXA library documentation.
Source: https://pyxa.readthedocs.io/en/latest/reference/apps/Safari.html

PyXA is a Python library for automating macOS applications using Apple's 
Accessibility and ScriptingBridge frameworks.
"""

from .base import getter
from typing import Dict, Any, List, Optional

@getter(
    name="safari_current_tab_html",
    os=["macos"],
    applications="Safari",
    description="Get HTML source of the current Safari tab"
)
def get_current_tab_html() -> Dict[str, Any]:
    """Get HTML source code of the currently active Safari tab."""
    try:
        import PyXA
        app = PyXA.Application("Safari")
        
        window = app.front_window
        if not window:
            return {"error": "No Safari window is open"}
        
        doc = app.current_document
        tab = window.current_tab
        
        if not tab:
            return {"error": "No active tab found"}
        
        return {
            "url": str(doc.url) if doc and hasattr(doc, 'url') else None,
            "title": str(doc.name) if doc and hasattr(doc, 'name') else None,
            "html": str(tab.source) if hasattr(tab, 'source') else None
        }
    except Exception as e:
        return {"error": f"Failed to get Safari tab HTML: {str(e)}"}

@getter(
    name="safari_all_tabs_html",
    os="macos",
    applications="Safari",
    description="Get HTML source of all open Safari tabs"
)
def get_all_tabs_html() -> Dict[str, Any]:
    """Get HTML source code of all open Safari tabs."""
    try:
        import PyXA
        app = PyXA.Application("Safari")
        
        tabs_data = []
        windows = app.windows()
        
        for window_idx, window in enumerate(windows):
            try:
                tabs = window.tabs()
                for tab_idx, tab in enumerate(tabs):
                    try:
                        tab_data = {
                            "window_index": window_idx,
                            "tab_index": tab_idx,
                            "url": str(tab.url) if hasattr(tab, 'url') else None,
                            "title": str(tab.name) if hasattr(tab, 'name') else None,
                            "html": str(tab.source) if hasattr(tab, 'source') else None,
                            "visible": tab.visible if hasattr(tab, 'visible') else None
                        }
                        tabs_data.append(tab_data)
                    except Exception as e:
                        # Skip tabs that can't be accessed
                        tabs_data.append({
                            "window_index": window_idx,
                            "tab_index": tab_idx,
                            "error": f"Could not access tab: {str(e)}"
                        })
            except Exception as e:
                # Skip windows that can't be accessed
                continue
        
        return {"tabs": tabs_data, "total_tabs": len(tabs_data)}
    except Exception as e:
        return {"error": f"Failed to get Safari tabs: {str(e)}"}

@getter(
    name="safari_current_tab_info",
    os="macos",
    applications="Safari",
    description="Get metadata about the current Safari tab (URL, title, etc) without HTML"
)
def get_current_tab_info() -> Dict[str, Any]:
    """Get information about the currently active Safari tab without the HTML source."""
    try:
        import PyXA
        app = PyXA.Application("Safari")
        
        window = app.front_window
        if not window:
            return {"error": "No Safari window is open"}
        
        doc = app.current_document
        tab = window.current_tab
        
        if not tab:
            return {"error": "No active tab found"}
        
        return {
            "url": str(tab.url) if hasattr(tab, 'url') else None,
            "title": str(tab.name) if hasattr(tab, 'name') else None,
            "index": tab.index if hasattr(tab, 'index') else None,
            "visible": tab.visible if hasattr(tab, 'visible') else None
        }
    except Exception as e:
        return {"error": f"Failed to get Safari tab info: {str(e)}"}

@getter(
    name="safari_bookmarks",
    os="macos",
    applications="Safari",
    description="Get Safari bookmarks (limited support)"
)
def get_bookmarks() -> Dict[str, Any]:
    """Get Safari bookmarks. Note: PyXA has limited bookmark support."""
    try:
        import PyXA
        app = PyXA.Application("Safari")
        
        # Note: PyXA's bookmark support is limited
        # This is a placeholder implementation
        return {
            "error": "Bookmark access is limited in PyXA. Consider using Safari's export feature or accessing bookmark files directly."
        }
    except Exception as e:
        return {"error": f"Failed to get bookmarks: {str(e)}"}

@getter(
    name="safari_window_info",
    os="macos",
    applications="Safari",
    description="Get information about all Safari windows and their tabs"
)
def get_window_info() -> Dict[str, Any]:
    """Get information about all Safari windows and their tabs."""
    try:
        import PyXA
        app = PyXA.Application("Safari")
        
        windows_data = []
        windows = app.windows()
        
        for window_idx, window in enumerate(windows):
            try:
                window_data = {
                    "index": window_idx,
                    "name": str(window.name) if hasattr(window, 'name') else None,
                    "id": str(window.id) if hasattr(window, 'id') else None,
                    "tabs": []
                }
                
                tabs = window.tabs()
                for tab_idx, tab in enumerate(tabs):
                    try:
                        tab_info = {
                            "index": tab_idx,
                            "url": str(tab.url) if hasattr(tab, 'url') else None,
                            "title": str(tab.name) if hasattr(tab, 'name') else None,
                            "visible": tab.visible if hasattr(tab, 'visible') else None
                        }
                        window_data["tabs"].append(tab_info)
                    except:
                        window_data["tabs"].append({"index": tab_idx, "error": "Could not access tab"})
                
                window_data["tab_count"] = len(window_data["tabs"])
                windows_data.append(window_data)
            except Exception as e:
                windows_data.append({"index": window_idx, "error": str(e)})
        
        return {
            "windows": windows_data,
            "total_windows": len(windows_data),
            "front_window_index": 0 if windows_data else None
        }
    except Exception as e:
        return {"error": f"Failed to get window info: {str(e)}"}
