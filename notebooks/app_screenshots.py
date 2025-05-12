#!/usr/bin/env python3
"""App Screenshots - A standalone script to capture screenshots of running macOS applications

This script captures screenshots of all running macOS applications and their windows,
preserving z-order information to allow for recomposition of the desktop.
"""

import sys
import os
import time
import argparse
from typing import List, Dict, Any, Optional, Tuple
import json
from PIL import Image, ImageDraw
import io
import asyncio
import functools

# Timing decorator for profiling
def timing_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Function {func.__name__} took {elapsed_time:.4f} seconds to run")
        return result
    return wrapper

# Import Objective-C bridge libraries
try:
    import Quartz
    import AppKit
    from ApplicationServices import (
        AXUIElementCreateSystemWide,  # type: ignore
        AXUIElementCreateApplication,  # type: ignore
        AXUIElementCopyAttributeValue,  # type: ignore
        AXUIElementCopyAttributeValues,  # type: ignore
        kAXFocusedWindowAttribute,  # type: ignore
        kAXWindowsAttribute,  # type: ignore
        kAXMainWindowAttribute,  # type: ignore
        kAXChildrenAttribute,  # type: ignore
        kAXRoleAttribute,  # type: ignore
        kAXTitleAttribute,  # type: ignore
        kAXValueAttribute,  # type: ignore
        kAXDescriptionAttribute,  # type: ignore
        kAXEnabledAttribute,  # type: ignore
        kAXPositionAttribute,  # type: ignore
        kAXSizeAttribute,  # type: ignore
        kAXErrorSuccess,  # type: ignore
        AXValueGetType,  # type: ignore
        kAXValueCGSizeType,  # type: ignore
        kAXValueCGPointType,  # type: ignore
        kAXValueCFRangeType,  # type: ignore
        AXUIElementGetTypeID,  # type: ignore
        AXValueGetValue,  # type: ignore
        kAXVisibleChildrenAttribute,  # type: ignore
        kAXRoleDescriptionAttribute,  # type: ignore
        kAXFocusedApplicationAttribute,  # type: ignore
        kAXFocusedUIElementAttribute,  # type: ignore
        kAXSelectedTextAttribute,  # type: ignore
        kAXSelectedTextRangeAttribute,  # type: ignore
    )
    from AppKit import NSWorkspace, NSApplication, NSApp, NSRunningApplication
    import Foundation
    from Foundation import NSObject, NSMakeRect
    import objc
except ImportError:
    print("Error: This script requires PyObjC to be installed.")
    print("Please install it with: pip install pyobjc")
    sys.exit(1)

# Constants for accessibility API
kAXErrorSuccess = 0
kAXRoleAttribute = "AXRole"
kAXTitleAttribute = "AXTitle"
kAXValueAttribute = "AXValue"
kAXWindowsAttribute = "AXWindows"
kAXFocusedAttribute = "AXFocused"
kAXPositionAttribute = "AXPosition"
kAXSizeAttribute = "AXSize"
kAXChildrenAttribute = "AXChildren"
kAXMenuBarAttribute = "AXMenuBar"
kAXMenuBarItemAttribute = "AXMenuBarItem"

# Constants for window properties
kCGWindowLayer = "kCGWindowLayer"  # Z-order information (lower values are higher in the stack)
kCGWindowAlpha = "kCGWindowAlpha"  # Window opacity

# Constants for application activation options
NSApplicationActivationOptions = {
    "regular": 0,  # Default activation
    "bringing_all_windows_forward": 1 << 0,  # NSApplicationActivateAllWindows
    "ignoring_other_apps": 1 << 1  # NSApplicationActivateIgnoringOtherApps
}


def CFAttributeToPyObject(attrValue):
    def list_helper(list_value):
        list_builder = []
        for item in list_value:
            list_builder.append(CFAttributeToPyObject(item))
        return list_builder

    def number_helper(number_value):
        success, int_value = Foundation.CFNumberGetValue(  # type: ignore
            number_value, Foundation.kCFNumberIntType, None  # type: ignore
        )
        if success:
            return int(int_value)

        success, float_value = Foundation.CFNumberGetValue(  # type: ignore
            number_value, Foundation.kCFNumberDoubleType, None  # type: ignore
        )
        if success:
            return float(float_value)
        return None

    def axuielement_helper(element_value):
        return element_value

    cf_attr_type = Foundation.CFGetTypeID(attrValue)  # type: ignore
    cf_type_mapping = {
        Foundation.CFStringGetTypeID(): str,  # type: ignore
        Foundation.CFBooleanGetTypeID(): bool,  # type: ignore
        Foundation.CFArrayGetTypeID(): list_helper,  # type: ignore
        Foundation.CFNumberGetTypeID(): number_helper,  # type: ignore
        AXUIElementGetTypeID(): axuielement_helper,  # type: ignore
    }
    try:
        return cf_type_mapping[cf_attr_type](attrValue)
    except KeyError:
        # did not get a supported CF type. Move on to AX type
        pass

    ax_attr_type = AXValueGetType(attrValue)
    ax_type_map = {
        kAXValueCGSizeType: Foundation.NSSizeFromString,  # type: ignore
        kAXValueCGPointType: Foundation.NSPointFromString,  # type: ignore
        kAXValueCFRangeType: Foundation.NSRangeFromString,  # type: ignore
    }
    try:
        search_result = re.search("{.*}", attrValue.description())
        if search_result:
            extracted_str = search_result.group()
            return tuple(ax_type_map[ax_attr_type](extracted_str))
        return None
    except KeyError:
        return None

def element_attribute(element, attribute):
    if attribute == kAXChildrenAttribute:
        err, value = AXUIElementCopyAttributeValues(element, attribute, 0, 999, None)
        if err == kAXErrorSuccess:
            if isinstance(value, Foundation.NSArray):  # type: ignore
                return CFAttributeToPyObject(value)
            else:
                return value
    err, value = AXUIElementCopyAttributeValue(element, attribute, None)
    if err == kAXErrorSuccess:
        if isinstance(value, Foundation.NSArray):  # type: ignore
            return CFAttributeToPyObject(value)
        else:
            return value
    return None

def element_value(element, type):
    err, value = AXValueGetValue(element, type, None)
    if err == True:
        return value
    return None


class AppScreenshotCapture:
    """Capture screenshots of running macOS applications"""
    
    def __init__(self, output_dir: str = None):
        """Initialize the screenshot capture
        
        Args:
            output_dir: Directory to save screenshots (if None, won't save to disk)
        """
        self.output_dir = output_dir
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    @timing_decorator
    def get_running_apps(self) -> List[NSRunningApplication]:
        """Get list of all running applications
        
        Returns:
            List of NSRunningApplication objects
        """
        return NSWorkspace.sharedWorkspace().runningApplications()
    
    # @timing_decorator
    def get_app_info(self, app: NSRunningApplication) -> Dict[str, Any]:
        """Get information about an application
        
        Args:
            app: NSRunningApplication object
            
        Returns:
            Dictionary with application information
        """
        return {
            "name": app.localizedName(),
            "bundle_id": app.bundleIdentifier(),
            "pid": app.processIdentifier(),
            "active": app.isActive(),
            "hidden": app.isHidden(),
            "terminated": app.isTerminated(),
        }
    
    @timing_decorator
    def get_all_windows(self) -> List[Dict[str, Any]]:
        """Get all windows from all applications with z-order information
        
        Returns:
            List of window dictionaries with z-order information
        """
        # Get all windows from Quartz
        # The kCGWindowListOptionOnScreenOnly flag gets only visible windows with preserved z-order
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID
        )
        
        # Create a dictionary of window z-order
        z_order = {window['kCGWindowNumber']: z_index for z_index, window in enumerate(window_list[::-1])}
        
        # The kCGWindowListOptionAll flag gets all windows *without* z-order preserved
        window_list_all = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionAll,
            Quartz.kCGNullWindowID
        )
        
        # Process all windows
        windows = []
        for window in window_list_all:
            # We track z_index which is the index in the window list (0 is the desktop / background)
            
            # Get window properties
            window_id = window.get('kCGWindowNumber', 0)
            window_name = window.get('kCGWindowName', '')
            window_pid = window.get('kCGWindowOwnerPID', 0)
            window_bounds = window.get('kCGWindowBounds', {})
            window_owner = window.get('kCGWindowOwnerName', '')
            window_is_on_screen = window.get('kCGWindowIsOnscreen', False)
            
            # Get z-order information
            # Note: kCGWindowLayer provides the system's layer value (lower values are higher in the stack)
            layer = window.get(kCGWindowLayer, 0)
            opacity = window.get(kCGWindowAlpha, 1.0)
            z_index = z_order.get(window_id, -1)
            
            # Determine window role (desktop, dock, menubar, app)
            if window_owner == "Window Server":
                if window_name == "Desktop":
                    role = "desktop"
                elif window_name == "Dock":
                    role = "dock"
                elif window_name == "Menubar":
                    role = "menubar"
            elif window_owner == "Dock":
                role = "dock"
            else:
                role = "app"
            
            # Only include windows with valid bounds
            if window_bounds:
                windows.append({
                    "id": window_id,
                    "name": window_name or "Unnamed Window",
                    "pid": window_pid,
                    "owner": window_owner,
                    "role": role,
                    "is_on_screen": window_is_on_screen,
                    "bounds": {
                        "x": window_bounds.get('X', 0),
                        "y": window_bounds.get('Y', 0),
                        "width": window_bounds.get('Width', 0),
                        "height": window_bounds.get('Height', 0)
                    },
                    "layer": layer,  # System layer (lower values are higher in stack)
                    "z_index": z_index,  # Our z-index (0 is the desktop)
                    "opacity": opacity
                })
                
        windows = sorted(windows, key=lambda x: x["z_index"])
        
        return windows
    
    def get_app_windows(self, app_pid: int, all_windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get all windows for a specific application
        
        Args:
            app_pid: Process ID of the application
            all_windows: List of all windows with z-order information
            
        Returns:
            List of window dictionaries for the app
        """
        # Filter windows by PID
        return [window for window in all_windows if window["pid"] == app_pid]
    
    @timing_decorator
    def capture_desktop_screenshot(self, app_filter: List[str] = None, all_windows: List[Dict[str, Any]] = None) -> Optional[Image.Image]:
        """Capture a screenshot of the entire desktop using Quartz compositing
        
        Args:
            app_filter: Optional list of app names to include in the screenshot
            
        Returns:
            PIL Image of the desktop or None if capture failed
        """
        # Get all windows with z-order information to determine which ones to include
        if all_windows is None:
            all_windows = self.get_all_windows()
        
        # Create a list of window IDs to include
        window_ids_to_include = []
        
        # Reverse the list to get the correct z-order
        for window in all_windows[::-1]:
            owner = window["owner"]
            name = window["name"]
            role = window["role"]
            is_on_screen = window["is_on_screen"]
            
            # Skip windows that are not on screen
            if not is_on_screen:
                continue

            # Skip app windows that are not in the filter
            if app_filter is not None and owner not in app_filter and role == "app":
                continue
            
            window_ids_to_include.append(window["id"])
        
        # Get the main screen dimensions
        main_screen = AppKit.NSScreen.mainScreen()
        screen_rect = None
        
        if main_screen:
            frame = main_screen.frame()
            screen_rect = Quartz.CGRectMake(
                0, 0,
                frame.size.width, frame.size.height
            )
        else:
            # Fallback to CGRectNull if we can't get the main screen
            screen_rect = Quartz.CGRectNull
            
        # If no filter is applied, capture the entire screen
        if app_filter is None:
            cg_image = Quartz.CGWindowListCreateImage(
                screen_rect,  # Capture only the main screen area
                Quartz.kCGWindowListOptionOnScreenOnly,  # Only capture on-screen windows
                Quartz.kCGNullWindowID,  # No specific window
                Quartz.kCGWindowImageDefault  # Include shadows
            )
        else:
            # Create a CFArray of window IDs to include
            window_list = Foundation.CFArrayCreateMutable(None, len(window_ids_to_include), None)
            for window_id in window_ids_to_include:
                Foundation.CFArrayAppendValue(window_list, window_id)
            
            # Capture only the specified windows
            cg_image = Quartz.CGWindowListCreateImageFromArray(
                screen_rect,  # Capture only the main screen area
                window_list,  # Array of window IDs to include
                Quartz.kCGWindowImageDefault  # Include shadows
            )
        
        if cg_image is None:
            return None
        
        # Convert CGImage to PNG data
        ns_image = AppKit.NSImage.alloc().initWithCGImage_size_(cg_image, Foundation.NSZeroSize)
        ns_data = ns_image.TIFFRepresentation()
        bitmap_rep = AppKit.NSBitmapImageRep.imageRepWithData_(ns_data)
        png_data = bitmap_rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, None)
        
        # Convert to PIL Image
        image_data = io.BytesIO(png_data)
        return Image.open(image_data)
    
    def get_menubar_items(self, active_app_pid: int = None) -> List[Dict[str, Any]]:
        """Get menubar items from the active application using Accessibility API
        
        Args:
            active_app_pid: PID of the active application
            
        Returns:
            List of dictionaries with menubar item information
        """
        menubar_items = []
        
        if active_app_pid is None:
            # Get the frontmost application's PID if none provided
            frontmost_app = NSWorkspace.sharedWorkspace().frontmostApplication()
            if frontmost_app:
                active_app_pid = frontmost_app.processIdentifier()
            else:
                print("Error: Could not determine frontmost application")
                return menubar_items
        
        # Create an accessibility element for the application
        app_element = AXUIElementCreateApplication(active_app_pid)
        if app_element is None:
            print(f"Error: Could not create accessibility element for PID {active_app_pid}")
            return menubar_items
        
        # Get the menubar
        menubar = element_attribute(app_element, kAXMenuBarAttribute)
        if menubar is None:
            print(f"Error: Could not get menubar for application with PID {active_app_pid}")
            return menubar_items
        
        # Get the menubar items
        children = element_attribute(menubar, kAXChildrenAttribute)
        if children is None:
            print("Error: Could not get menubar items")
            return menubar_items
        
        # Process each menubar item
        for i in range(len(children)):
            item = children[i]
            
            # Get item title
            title = element_attribute(item, kAXTitleAttribute) or "Untitled"
            
            # Create bounding box
            bounds = {
                "x": 0,
                "y": 0,
                "width": 0,
                "height": 0
            }
            
            # Get item position
            position_value = element_attribute(item, kAXPositionAttribute)
            if position_value:
                position_value = element_value(position_value, kAXValueCGPointType)
                bounds["x"] = position_value.x
                bounds["y"] = position_value.y
            
            # Get item size
            size_value = element_attribute(item, kAXSizeAttribute)
            if size_value:
                size_value = element_value(size_value, kAXValueCGSizeType)
                bounds["width"] = size_value.width
                bounds["height"] = size_value.height
            
            
            # Add to list
            menubar_items.append({
                "title": title,
                "bounds": bounds,
                "index": i,
                "app_pid": active_app_pid
            })
        
        return menubar_items
        
    @timing_decorator
    def get_dock_items(self) -> List[Dict[str, Any]]:
        """Get all items in the macOS Dock
        
        Returns:
            List of dictionaries with Dock item information
        """
        dock_items = []
        
        # Find the Dock process
        dock_pid = None
        running_apps = self.get_running_apps()
        for app in running_apps:
            if app.localizedName() == "Dock" and app.bundleIdentifier() == "com.apple.dock":
                dock_pid = app.processIdentifier()
                break
                
        if dock_pid is None:
            print("Error: Could not find Dock process")
            return dock_items
            
        # Create an accessibility element for the Dock
        dock_element = AXUIElementCreateApplication(dock_pid)
        if dock_element is None:
            print(f"Error: Could not create accessibility element for Dock (PID {dock_pid})")
            return dock_items
            
        # Get the Dock's main element
        dock_list = element_attribute(dock_element, kAXChildrenAttribute)
        if dock_list is None or len(dock_list) == 0:
            print("Error: Could not get Dock children")
            return dock_items
            
        # Find the Dock's application list (usually the first child)
        dock_app_list = None
        for child in dock_list:
            role = element_attribute(child, kAXRoleAttribute)
            if role == "AXList":
                dock_app_list = child
                break
                
        if dock_app_list is None:
            print("Error: Could not find Dock application list")
            return dock_items
            
        # Get all items in the Dock
        items = element_attribute(dock_app_list, kAXChildrenAttribute)
        if items is None:
            print("Error: Could not get Dock items")
            return dock_items
            
        # Process each Dock item
        for i, item in enumerate(items):
            # Get item attributes
            title = element_attribute(item, kAXTitleAttribute) or "Untitled"
            description = element_attribute(item, "AXDescription") or ""
            role = element_attribute(item, kAXRoleAttribute) or ""
            subrole = element_attribute(item, "AXSubrole") or ""
            
            # Create bounding box
            bounds = {
                "x": 0,
                "y": 0,
                "width": 0,
                "height": 0
            }
            
            # Get item position
            position_value = element_attribute(item, kAXPositionAttribute)
            if position_value:
                position_value = element_value(position_value, kAXValueCGPointType)
                bounds["x"] = position_value.x
                bounds["y"] = position_value.y
            
            # Get item size
            size_value = element_attribute(item, kAXSizeAttribute)
            if size_value:
                size_value = element_value(size_value, kAXValueCGSizeType)
                bounds["width"] = size_value.width
                bounds["height"] = size_value.height
                
            # Determine if this is an application, file/folder, or separator
            item_type = "unknown"
            if subrole == "AXApplicationDockItem":
                item_type = "application"
            elif subrole == "AXFolderDockItem":
                item_type = "folder"
            elif subrole == "AXDocumentDockItem":
                item_type = "document"
            elif subrole == "AXSeparatorDockItem" or role == "AXSeparator":
                item_type = "separator"
            elif "trash" in title.lower():
                item_type = "trash"
                
            # Add to list
            dock_items.append({
                "title": title,
                "description": description,
                "bounds": bounds,
                "index": i,
                "type": item_type,
                "role": role,
                "subrole": subrole
            })
            
        return dock_items
    
    def capture_all_apps(self, save_to_disk: bool = False, create_composite: bool = False, 
                         app_filter: List[str] = None) -> Dict[str, Any]:
        """Capture screenshots of all running applications
        
        Args:
            save_to_disk: Whether to save screenshots to disk
            create_composite: Whether to create a recomposited screenshot
            app_filter: Optional list of app names to include in the recomposited screenshot
                       (will always include 'Window Server' and 'Dock')
            
        Returns:
            Dictionary with application information and screenshots
        """
        result = {
            "timestamp": time.time(),
            "applications": [],
            "windows": [],  # New array to store all windows, including those without apps
            "menubar_items": [],  # New array to store menubar items
            "dock_items": []  # New array to store dock items
        }
        
        # Get all windows with z-order information
        all_windows = self.get_all_windows()
        
        # Get all running applications
        running_apps = self.get_running_apps()
        
        # Save the currently frontmost app before making any changes
        frontmost_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        
        # Automatically determine the active app based on the topmost non-filtered app
        active_app_to_use = None
        active_app_pid = None
        
        # Find the topmost (highest z_index) non-filtered app
        for window in all_windows[::-1]:
            owner = window.get("owner")
            role = window.get("role")
            
            # Skip non-app windows
            if role != "app":
                continue
            
            # Skip filtered apps
            if app_filter is not None and owner not in app_filter:
                continue
                
            # Found a suitable app
            active_app_to_use = owner
            active_app_pid = window.get("pid")
            break
        
        # If no suitable app found, use Finder
        if active_app_to_use is None:
            active_app_to_use = "Finder"
            # Find Finder's PID
            for app in running_apps:
                if app.localizedName() == "Finder":
                    active_app_pid = app.processIdentifier()
                    break
        
        print(f"Automatically activating app '{active_app_to_use}' for screenshot composition")
        
        # Activate the selected application
        if active_app_pid:
            # Get all running applications
            running_apps_list = NSWorkspace.sharedWorkspace().runningApplications()
            
            # Find the NSRunningApplication object for the active app
            for app in running_apps_list:
                if app.processIdentifier() == active_app_pid:
                    app.activateWithOptions_(0)
                    break
        
        # Process applications
        for app in running_apps:
            # Skip system apps without a bundle ID
            if app.bundleIdentifier() is None:
                continue
                
            app_info = self.get_app_info(app)
            app_windows = self.get_app_windows(app.processIdentifier(), all_windows)
            
            app_data = {
                "info": app_info,
                "windows": [ window["id"] for window in app_windows ]
            }
            
            result["applications"].append(app_data)
        
        # Get menubar items from the active application
        menubar_items = self.get_menubar_items(active_app_pid)
        result["menubar_items"] = menubar_items
        
        # Get dock items
        dock_items = self.get_dock_items()
        result["dock_items"] = dock_items
        
        # Add all windows to the result
        result["windows"] = all_windows
        
        # Capture the entire desktop using Quartz compositing
        desktop_screenshot = self.capture_desktop_screenshot(app_filter, all_windows)
        
        if desktop_screenshot and save_to_disk and self.output_dir:
            desktop_path = os.path.join(self.output_dir, "desktop.png")
            desktop_screenshot.save(desktop_path)
            result["desktop_screenshot"] = desktop_path
        
        # Switch focus back to the originally frontmost app
        if frontmost_app:
            frontmost_app.activateWithOptions_(0)
        
        return result


async def run_capture():
    """Run the screenshot capture asynchronously"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Capture screenshots of running macOS applications")
    parser.add_argument("--output", "-o", help="Output directory for screenshots", default="app_screenshots")
    parser.add_argument("--composite", "-c", action="store_true", help="Create a recomposited screenshot")
    parser.add_argument("--filter", "-f", nargs="+", help="Filter recomposited screenshot to only include specified apps")
    parser.add_argument("--menubar", "-m", action="store_true", help="List menubar and status items with their bounding boxes")
    parser.add_argument("--dock", "-d", action="store_true", help="List Dock items with their bounding boxes")
    args = parser.parse_args()
    
    # Create output directory in the current directory if not absolute
    if not os.path.isabs(args.output):
        output_dir = os.path.join(os.getcwd(), args.output)
    else:
        output_dir = args.output
    
    # Create the screenshot capture
    capture = AppScreenshotCapture(output_dir)
    
    # Capture all apps and save to disk, including a recomposited screenshot
    print(f"Capturing screenshots of all running applications...")
    print(f"Saving screenshots to: {output_dir}")
    
    # If filter is provided, show what we're filtering by
    if args.filter:
        print(f"Filtering recomposited screenshot to only include: {', '.join(args.filter)} (plus Window Server and Dock)")
    
    result = capture.capture_all_apps(
        save_to_disk=True, 
        create_composite=args.composite, 
        app_filter=args.filter
    )
    
    # Print summary
    print(f"\nCapture complete!")
    print(f"Captured {len(result['applications'])} applications")
    
    total_app_windows = sum(len(app["windows"]) for app in result["applications"])
    print(f"Total application windows captured: {total_app_windows}")
    print(f"Total standalone windows captured: {len(result['windows'])}")
    
    # Print details of each application
    print("\nApplication details:")
    for app in result["applications"]:
        app_info = app["info"]
        windows = app["windows"]
        print(f"  - {app_info['name']} ({len(windows)} windows)")
    
    # Print recomposited screenshot path if available
    if "desktop_screenshot" in result:
        print(f"\nRecomposited screenshot saved to: {result['desktop_screenshot']}")
    
    # Print menubar items if requested
    if args.menubar and "menubar_items" in result:
        print("\nMenubar items:")
        
        # Find app name for the PID
        app_name_by_pid = {}
        for app in result["applications"]:
            app_info = app["info"]
            app_name_by_pid[app_info["pid"]] = app_info["name"]
            
        for item in result["menubar_items"]:
            print(f"  - {item['title']}")
            print(f"    Bounds: x={item['bounds']['x']}, y={item['bounds']['y']}, width={item['bounds']['width']}, height={item['bounds']['height']}")
            
            if "app_pid" in item:
                app_name = app_name_by_pid.get(item["app_pid"], f"Unknown App (PID: {item['app_pid']})")
                print(f"    App: {app_name} (PID: {item['app_pid']})")
                
            if "window_id" in item:
                print(f"    Window ID: {item['window_id']}")
            if "owner" in item:
                print(f"    Owner: {item['owner']}")
            if "layer" in item and "z_index" in item:
                print(f"    Layer: {item['layer']}, Z-Index: {item['z_index']}")
            print("")
    
    # Print dock items if requested
    if args.dock and "dock_items" in result:
        print("\nDock items:")
        for item in result["dock_items"]:
            print(f"  - {item['title']} ({item['type']})")
            print(f"    Description: {item['description']}")
            print(f"    Bounds: x={item['bounds']['x']}, y={item['bounds']['y']}, width={item['bounds']['width']}, height={item['bounds']['height']}")
            print(f"    Role: {item['role']}, Subrole: {item['subrole']}")
            print(f"    Index: {item['index']}")
            print("")
    
    # Save the metadata to a JSON file
    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\nMetadata saved to: {metadata_path}")

def main():
    """Main entry point"""
    asyncio.run(run_capture())


if __name__ == "__main__":
    main()