"""
Decorators for agent2 - agent_loop decorator
"""

import asyncio
import inspect
from typing import Dict, List, Any, Callable, Optional
from functools import wraps

from .types import AgentLoopInfo

# Global registry
_agent_loops: List[AgentLoopInfo] = []

def agent_loop(models: str, priority: int = 0):
    """
    Decorator to register an agent loop function.
    
    Args:
        models: Regex pattern to match supported models
        priority: Priority for loop selection (higher = more priority)
    """
    def decorator(func: Callable):
        # Validate function signature
        sig = inspect.signature(func)
        required_params = {'messages', 'model'}
        func_params = set(sig.parameters.keys())
        
        if not required_params.issubset(func_params):
            missing = required_params - func_params
            raise ValueError(f"Agent loop function must have parameters: {missing}")
        
        # Register the loop
        loop_info = AgentLoopInfo(
            func=func,
            models_regex=models,
            priority=priority
        )
        _agent_loops.append(loop_info)
        
        # Sort by priority (highest first)
        _agent_loops.sort(key=lambda x: x.priority, reverse=True)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Wrap the function in an asyncio.Queue for cancellation support
            queue = asyncio.Queue()
            task = None
            
            try:
                # Create a task that can be cancelled
                async def run_loop():
                    try:
                        result = await func(*args, **kwargs)
                        await queue.put(('result', result))
                    except Exception as e:
                        await queue.put(('error', e))
                
                task = asyncio.create_task(run_loop())
                
                # Wait for result or cancellation
                event_type, data = await queue.get()
                
                if event_type == 'error':
                    raise data
                return data
                
            except asyncio.CancelledError:
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                raise
        
        return wrapper
    
    return decorator

def get_agent_loops() -> List[AgentLoopInfo]:
    """Get all registered agent loops"""
    return _agent_loops.copy()

def find_agent_loop(model: str) -> Optional[AgentLoopInfo]:
    """Find the best matching agent loop for a model"""
    for loop_info in _agent_loops:
        if loop_info.matches_model(model):
            return loop_info
    return None
