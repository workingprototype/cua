"""Example demonstrating the ComputerAgent capabilities with the Omni provider."""

import asyncio
import logging
import traceback
import signal

from computer import Computer, VMProviderType

# Import the unified agent class and types
from agent import ComputerAgent, LLMProvider, LLM, AgentLoop

# Import utility functions
from utils import load_dotenv_files, handle_sigint

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_agent_example():
    """Run example of using the ComputerAgent with OpenAI and Omni provider."""
    print("\n=== Example: ComputerAgent with OpenAI and Omni provider ===")

    try:
        # Create a local macOS computer
        computer = Computer(
            os_type="macos",
            verbosity=logging.DEBUG,
        )

        # Create a remote Linux computer with Cua
        # computer = Computer(
        #     os_type="linux",
        #     api_key=os.getenv("CUA_API_KEY"),
        #     name=os.getenv("CUA_CONTAINER_NAME"),
        #     provider_type=VMProviderType.CLOUD,
        # )

        # Create Computer instance with async context manager
        agent = ComputerAgent(
            computer=computer,
            loop=AgentLoop.OPENAI,
            # loop=AgentLoop.ANTHROPIC,
            # loop=AgentLoop.UITARS,
            # loop=AgentLoop.OMNI,
            model=LLM(provider=LLMProvider.OPENAI),  # No model name for Operator CUA
            # model=LLM(provider=LLMProvider.OPENAI, name="gpt-4o"),
            # model=LLM(provider=LLMProvider.ANTHROPIC, name="claude-3-7-sonnet-20250219"),
            # model=LLM(provider=LLMProvider.OLLAMA, name="gemma3:4b-it-q4_K_M"),
            # model=LLM(provider=LLMProvider.MLXVLM, name="mlx-community/UI-TARS-1.5-7B-4bit"),
            # model=LLM(
            #     provider=LLMProvider.OAICOMPAT,
            #     name="gemma-3-12b-it",
            #     provider_base_url="http://localhost:1234/v1",  # LM Studio local endpoint
            # ),
            save_trajectory=True,
            only_n_most_recent_images=3,
            verbosity=logging.DEBUG,
        )

        tasks = [
            "Look for a repository named trycua/cua on GitHub.",
            "Check the open issues, open the most recent one and read it.",
            "Clone the repository in users/lume/projects if it doesn't exist yet.",
            "Open the repository with an app named Cursor (on the dock, black background and white cube icon).",
            "From Cursor, open Composer if not already open.",
            "Focus on the Composer text area, then write and submit a task to help resolve the GitHub issue.",
        ]

        for i, task in enumerate(tasks):
            print(f"\nExecuting task {i}/{len(tasks)}: {task}")
            async for result in agent.run(task):
                print("Response ID: ", result.get("id"))

                # Print detailed usage information
                usage = result.get("usage")
                if usage:
                    print("\nUsage Details:")
                    print(f"  Input Tokens: {usage.get('input_tokens')}")
                    if "input_tokens_details" in usage:
                        print(f"  Input Tokens Details: {usage.get('input_tokens_details')}")
                    print(f"  Output Tokens: {usage.get('output_tokens')}")
                    if "output_tokens_details" in usage:
                        print(f"  Output Tokens Details: {usage.get('output_tokens_details')}")
                    print(f"  Total Tokens: {usage.get('total_tokens')}")

                print("Response Text: ", result.get("text"))

                # Print tools information
                tools = result.get("tools")
                if tools:
                    print("\nTools:")
                    print(tools)

                # Print reasoning and tool call outputs
                outputs = result.get("output", [])
                for output in outputs:
                    output_type = output.get("type")
                    if output_type == "reasoning":
                        print("\nReasoning Output:")
                        print(output)
                    elif output_type == "computer_call":
                        print("\nTool Call Output:")
                        print(output)

            print(f"\n✅ Task {i+1}/{len(tasks)} completed: {task}")

    except Exception as e:
        logger.error(f"Error in run_agent_example: {e}")
        traceback.print_exc()
        raise


def main():
    """Run the Anthropic agent example."""
    try:
        load_dotenv_files()

        # Register signal handler for graceful exit
        signal.signal(signal.SIGINT, handle_sigint)

        asyncio.run(run_agent_example())
    except Exception as e:
        print(f"Error running example: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
