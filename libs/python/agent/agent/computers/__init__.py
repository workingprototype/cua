"""
Computer handler factory and interface definitions.

This module provides a factory function to create computer handlers from different
computer interface types, supporting both the ComputerHandler protocol and the
Computer library interface.
"""

from .base import ComputerHandler
from .cua import cuaComputerHandler
from computer import Computer

def make_computer_handler(computer):
    """
    Create a computer handler from a computer interface.
    
    Args:
        computer: Either a ComputerHandler instance or a Computer instance
        
    Returns:
        ComputerHandler: A computer handler instance
        
    Raises:
        ValueError: If the computer type is not supported
    """
    if isinstance(computer, ComputerHandler):
        return computer
    if isinstance(computer, Computer):
        return cuaComputerHandler(computer)
    raise ValueError(f"Unsupported computer type: {type(computer)}")