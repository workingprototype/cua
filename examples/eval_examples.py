import os
import asyncio
from pathlib import Path
import sys
import traceback
import time

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
from computer.logger import LogLevel

# Assuming these exist based on your request
from agent import ComputerAgent, LLM, AgentLoop, LLMProvider

async def main():
    try:
        print("\n=== Using cloud container ===")
        # Create a remote Linux computer with CUA
        computer = Computer(
            os_type="linux",
            api_key=os.getenv("CUA_API_KEY"),
            name=str(os.getenv("CUA_CONTAINER_NAME")),
            provider_type=VMProviderType.CLOUD,
        )
        
        try:
            # Run the computer with default parameters
            await computer.run()
            
            # Install required packages
            await computer.venv_install("eval_env", ["pywinctl", "selenium", "beautifulsoup4"])

            # Helper functions for wikirace
            async def open_wiki(page):
                await computer.interface.run_command(f"firefox https://en.wikipedia.org/wiki/{page.replace(' ', '_')} &")
                await asyncio.sleep(2)  # Wait for page to load

            # Remote functions for wikirace
            def get_open_wikis():
                import pywinctl
                titles = pywinctl.getAllTitles()
                wiki_titles = [title.split(" - Wikipedia")[0] for title in titles if "Wikipedia" in title]
                return wiki_titles

            def get_current_wiki_page():
                import pywinctl
                titles = pywinctl.getAllTitles()
                wiki_titles = [title for title in titles if "Wikipedia" in title and "Mozilla Firefox" in title]
                if wiki_titles:
                    return wiki_titles[0].split(" - Wikipedia")[0]
                return None

            # Wikirace setup
            start_page = "Albert Einstein"
            target_page = "Pizza"
            max_steps = 10
            
            print(f"\nStarting Wikirace: {start_page} → {target_page}")
            
            # Open starting page
            await open_wiki(start_page)
            
            # Create agent
            agent = ComputerAgent(
                computer=computer,
                loop=AgentLoop.OPENAI,
                model=LLM(LLMProvider.OPENAI)
            )
            
            # Run the wikirace
            steps = 0
            success = False
            start_time = time.time()
            
            prompt = f"""
            You are playing Wikirace! Your goal is to navigate from "{start_page}" to "{target_page}" 
            by clicking only on Wikipedia links within articles.
            
            Rules:
            1. Only click on links within Wikipedia articles (blue underlined text)
            2. No using search, back button, or typing URLs
            3. Try to find the shortest path possible
            4. Current target: {target_page}
            
            Look at the current page and click on a link that might lead you closer to {target_page}.
            """
            
            async for step_result in agent.run(prompt):
                steps += 1
                print(f"Step {steps}: {step_result}")
                
                # Check current page
                current_page = await computer.venv_exec("eval_env", get_current_wiki_page)
                print(f"Current page: {current_page}")
                
                # Check if we reached the target
                if current_page and target_page.lower() in current_page.lower():
                    success = True
                    print(f"🎉 SUCCESS! Reached {target_page} in {steps} steps!")
                    break
                
                # Safety check
                if steps >= max_steps:
                    print(f"❌ Failed: Reached maximum steps ({max_steps})")
                    break
                
                await asyncio.sleep(1)  # Brief pause between steps
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Results
            print(f"\n=== WIKIRACE RESULTS ===")
            print(f"Start: {start_page}")
            print(f"Target: {target_page}")
            print(f"Steps taken: {steps}")
            print(f"Success: {success}")
            print(f"Duration: {duration:.2f} seconds")
            
            # Get final page list
            final_wikis = await computer.venv_exec("eval_env", get_open_wikis)
            print(f"Open Wikipedia pages: {final_wikis}")

        finally:
            # Important to clean up resources
            await computer.stop()
            
    except Exception as e:
        print(f"Error in main: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())