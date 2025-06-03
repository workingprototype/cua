"""
Virtual Environment Testing Module
This module tests the ability to execute python code in a virtual environment within C/ua Containers.

Required environment variables:
- CUA_API_KEY: API key for C/ua cloud provider
- CUA_CONTAINER_NAME: Name of the container to use
"""

import os
import asyncio
import pytest
from pathlib import Path
import sys
import traceback

# Load environment variables from .env file
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
print(f"Loading environment from: {env_file}")
from dotenv import load_dotenv

load_dotenv(env_file)

# Add paths to sys.path if needed
pythonpath = os.environ.get("PYTHONPATH", "")
for path in pythonpath.split(":"):
    if path and path not in sys.path:
        sys.path.insert(0, path)  # Insert at beginning to prioritize
        print(f"Added to sys.path: {path}")

from computer.computer import Computer
from computer.providers.base import VMProviderType


@pytest.fixture(scope="session")
async def computer():
    """Shared Computer instance for all test cases."""
    # Create a remote Linux computer with C/ua
    computer = Computer(
        os_type="linux",
        api_key=os.getenv("CUA_API_KEY"),
        name=str(os.getenv("CUA_CONTAINER_NAME")),
        provider_type=VMProviderType.CLOUD,
    )
    
    try:
        await computer.run()
        yield computer
    finally:
        await computer.stop()


# Sample test cases
@pytest.mark.asyncio(loop_scope="session")
async def test_venv_install(computer):
    """Test virtual environment creation and package installation."""
    # Create a test virtual environment and install requests
    stdout, _ = await computer.venv_install("test_env", ["requests"])
    
    # Check that installation was successful (no major errors)
    assert "Successfully installed" in stdout or "Requirement already satisfied" in stdout

@pytest.mark.asyncio(loop_scope="session")
async def test_venv_cmd(computer):
    """Test executing shell commands in virtual environment."""
    # Test Python version check
    stdout, _ = await computer.venv_cmd("test_env", "python --version")
    
    assert "Python" in stdout

@pytest.mark.asyncio(loop_scope="session")
async def test_venv_exec(computer):
    """Test executing Python functions in virtual environment."""
    def test_function(message="Hello World"):
        import sys
        return f"Python {sys.version_info.major}.{sys.version_info.minor}: {message}"
    
    result = await computer.venv_exec("test_env", test_function, message="Test successful!")
    
    assert "Python" in result
    assert "Test successful!" in result

@pytest.mark.asyncio(loop_scope="session")
async def test_venv_exec_with_package(computer):
    """Test executing Python functions that use installed packages."""
    def test_requests():
        import requests
        return f"requests version: {requests.__version__}"
    
    result = await computer.venv_exec("test_env", test_requests)
    
    assert "requests version:" in result

@pytest.mark.asyncio(loop_scope="session")
async def test_venv_exec_error_handling(computer):
    """Test error handling in venv_exec."""
    def test_error():
        raise ValueError("This is a test error")
    
    with pytest.raises(ValueError, match="This is a test error"):
        await computer.venv_exec("test_env", test_error)

@pytest.mark.asyncio(loop_scope="session")
async def test_venv_exec_with_args_kwargs(computer):
    """Test executing Python functions with args and kwargs that return an object."""
    def create_data_object(name, age, *hobbies, **metadata):
        return {
            "name": name,
            "age": age,
            "hobbies": list(hobbies),
            "metadata": metadata,
            "status": "active"
        }
    
    args = ["Alice", 25, "reading", "coding"]
    kwargs = {"location": "New York", "department": "Engineering"}

    result = await computer.venv_exec(
        "test_env", 
        create_data_object, 
        *args, 
        **kwargs
    )
    
    assert result["name"] == "Alice"
    assert result["age"] == 25
    assert result["hobbies"] == ["reading", "coding"]
    assert result["metadata"]["location"] == "New York"
    assert result["status"] == "active"

@pytest.mark.asyncio(loop_scope="session")
async def test_venv_exec_stdout_capture(computer, capfd):
    """Test capturing stdout from Python functions executed in virtual environment."""
    def hello_world_function():
        print("Hello World!")
        return "Function completed"
    
    # Execute the function in the virtual environment
    result = await computer.venv_exec("test_env", hello_world_function)
    
    # Capture stdout and stderr
    out, _ = capfd.readouterr()
    
    # Assert the stdout contains our expected output
    assert out == "Hello World!\n\n"
    assert result == "Function completed"

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
