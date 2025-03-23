"""Example demonstrating the ComputerAgent capabilities with the Omni provider."""

import os
import asyncio
import logging
import traceback
from pathlib import Path
import signal

from computer import Computer

# Import the unified agent class and types
from agent import AgentLoop, LLMProvider, LLM
from agent.core.computer_agent import ComputerAgent

# Import utility functions
from utils import load_dotenv_files, handle_sigint

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_omni_agent_example():
    """Run example of using the ComputerAgent with OpenAI and Omni provider."""
    print("\n=== Example: ComputerAgent with OpenAI and Omni provider ===")

    try:
        # Create Computer instance with default parameters
        computer = Computer(verbosity=logging.DEBUG)

        # Create agent with loop and provider
        agent = ComputerAgent(
            computer=computer,
            loop=AgentLoop.ANTHROPIC,
            # loop=AgentLoop.OMNI,
            # model=LLM(provider=LLMProvider.OPENAI, name="gpt-4.5-preview"),
            model=LLM(provider=LLMProvider.ANTHROPIC, name="claude-3-7-sonnet-20250219"),
            save_trajectory=True,
            trajectory_dir=str(Path("trajectories")),
            only_n_most_recent_images=3,
            verbosity=logging.INFO,
        )

        tasks = [
            """
1. Look for a repository named trycua/lume on GitHub.
2. Check the open issues, open the most recent one and read it.
3. Clone the repository in users/lume/projects if it doesn't exist yet.
4. Open the repository with an app named Cursor (on the dock, black background and white cube icon).
5. From Cursor, open Composer if not already open.
6. Focus on the Composer text area, then write and submit a task to help resolve the GitHub issue.
"""
        ]

        async with agent:
            for i, task in enumerate(tasks, 1):
                print(f"\nExecuting task {i}/{len(tasks)}: {task}")
                async for result in agent.run(task):
                    # Check if result has the expected structure
                    if "role" in result and "content" in result and "metadata" in result:
                        title = result["metadata"].get("title", "Screen Analysis")
                        content = result["content"]
                    else:
                        title = result.get("metadata", {}).get("title", "Screen Analysis")
                        content = result.get("content", str(result))

                    print(f"\n{title}")
                    print(content)
                print(f"Task {i} completed")

    except Exception as e:
        logger.error(f"Error in run_omni_agent_example: {e}")
        traceback.print_exc()
        raise
    finally:
        # Clean up resources
        if computer and computer._initialized:
            try:
                # await computer.stop()
                pass
            except Exception as e:
                logger.warning(f"Error stopping computer: {e}")


def main():
    """Run the Anthropic agent example."""
    try:
        load_dotenv_files()

        # Register signal handler for graceful exit
        signal.signal(signal.SIGINT, handle_sigint)

        asyncio.run(run_omni_agent_example())
    except Exception as e:
        print(f"Error running example: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
