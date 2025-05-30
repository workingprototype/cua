# Getter Plugin System

The getter plugin system allows you to easily add application-specific data extractors to the computer interface.

## Directory Structure

```
getters/
├── __init__.py      # Auto-imports all getter modules
├── base.py          # Base decorator and registry system
├── safari.py        # Safari-specific getters
├── chrome.py        # Chrome-specific getters (future)
├── vscode.py        # VS Code-specific getters (future)
└── README.md        # This file
```

## Creating a New Getter

To create a new getter, simply add a Python file in this directory and use the `@getter` decorator:

```python
from .base import getter

@getter(
    name="my_getter_name",
    os="macos",  # or ["macos", "linux"] or None for all
    applications="MyApp",  # or ["App1", "App2"] or "all"
    description="What this getter does"
)
def my_getter_function(**kwargs):
    """Docstring describing the getter."""
    try:
        # Your getter logic here
        return {"data": "your_data"}
    except Exception as e:
        return {"error": str(e)}
```

## Getter Decorator Parameters

- **name**: Unique identifier for the getter (e.g., "safari_current_tab_html")
- **os**: Supported operating systems
  - `"macos"`, `"linux"`, `"windows"` - Single OS
  - `["macos", "linux"]` - Multiple OS
  - `None` - All operating systems
- **applications**: Required applications
  - `"Safari"` - Single application
  - `["Safari", "Chrome"]` - Multiple applications
  - `"all"` - Works with any application
- **description**: Human-readable description

## Return Format

Getters should return a dictionary with either:
- Success: `{"data": <your_data>}` or just the data directly
- Error: `{"error": "Error message"}`

## Using Getters

Getters can be used through the `get_screen_data` method:

```python
# Get Safari tab HTML
result = await computer.interface.get_screen_data(
    getter_types=["safari_current_tab_html"]
)

# Use multiple getters
result = await computer.interface.get_screen_data(
    getter_types=["accessibility_tree", "safari_current_tab_html"]
)
```

## Available Safari Getters

1. **safari_current_tab_html** - Get HTML source of the current tab
2. **safari_all_tabs_html** - Get HTML source of all open tabs
3. **safari_current_tab_info** - Get tab metadata without HTML
4. **safari_execute_javascript** - Execute JavaScript in current tab
5. **safari_window_info** - Get information about all windows and tabs
6. **safari_reading_list** - Add URL to reading list
7. **safari_bookmarks** - Get bookmarks (limited support)

## Example: Adding a Chrome Getter

Create `chrome.py`:

```python
from .base import getter

@getter(
    name="chrome_current_tab_url",
    os="macos",
    applications="Google Chrome",
    description="Get current Chrome tab URL"
)
def get_current_tab_url():
    try:
        import PyXA
        app = PyXA.Application("Google Chrome")
        
        if not app.running:
            return {"error": "Chrome is not running"}
        
        window = app.front_window
        if window and window.active_tab:
            return {
                "url": str(window.active_tab.url),
                "title": str(window.active_tab.title)
            }
        
        return {"error": "No active tab found"}
    except Exception as e:
        return {"error": str(e)}
```

The getter will be automatically registered and available for use!
