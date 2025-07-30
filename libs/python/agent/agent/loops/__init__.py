"""
Agent loops for agent
"""

# Import the loops to register them
from . import anthropic
from . import openai
from . import uitars
from . import omniparser
from . import gta1

__all__ = ["anthropic", "openai", "uitars", "omniparser", "gta1"]
