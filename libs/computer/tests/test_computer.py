"""Basic tests for the computer package."""

import pytest
from computer import Computer

def test_computer_import():
    """Test that we can import the Computer class."""
    assert Computer is not None

def test_computer_init():
    """Test that we can create a Computer instance."""
    computer = Computer(
        display={"width": 1920, "height": 1080},
        memory="16GB",
        cpu="4",
        use_host_computer_server=True
    )
    assert computer is not None 