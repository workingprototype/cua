"""HUD integration for ComputerAgent."""

from typing import Any, Optional, Dict
from hud import run_job as hud_run_job

from .agent import ComputerAgent
from .adapter import ComputerAgentAdapter
from .computer_handler import HUDComputerHandler


async def run_job(
    model: str,
    task_or_taskset: Any,
    job_name: str,
    job_kwargs: Optional[Dict[str, Any]] = None,
    **agent_kwargs: Any
) -> Any:
    """
    Run a job using ComputerAgent with the specified model.
    
    Args:
        model: Model string for ComputerAgent (e.g., "anthropic/claude-3-5-sonnet-20241022")
        task_or_taskset: Task or TaskSet to run
        job_name: Name for the job
        **agent_kwargs: Additional kwargs to pass to ComputerAgent
    
    Returns:
        Job instance from HUD
    """
    return await hud_run_job(
        agent_cls=ComputerAgent,
        agent_kwargs={"model": model, **agent_kwargs},
        task_or_taskset=task_or_taskset,
        job_name=job_name,
        **job_kwargs or {}
    )


__all__ = ["ComputerAgent", "ComputerAgentAdapter", "HUDComputerHandler", "run_job"]