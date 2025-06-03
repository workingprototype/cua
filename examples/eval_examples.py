import os
import asyncio
from pathlib import Path
import sys
import traceback
import time
from functools import wraps

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
from computer.helpers import sandboxed

# Assuming these exist based on your request
from agent import ComputerAgent, LLM, AgentLoop, LLMProvider

async def main():    
    try:
        print("\n=== Using cloud container ===")
        # # Create a remote Linux computer with CUA
        # computer = Computer(
        #     os_type="linux",
        #     api_key=os.getenv("CUA_API_KEY"),
        #     name=str(os.getenv("CUA_CONTAINER_NAME")),
        #     provider_type=VMProviderType.CLOUD,
        # )
        
        # Connect to local macOS computer
        computer = Computer()
        
        try:
            # Run the computer with default parameters
            await computer.run()
            
            # Install required packages
            await computer.venv_install("eval_env", ["pywinctl", "selenium", "beautifulsoup4"])

            # Helper functions for wikirace
            async def open_wiki(page):
                await computer.interface.run_command(f"open https://en.wikipedia.org/wiki/{page.replace(' ', '_')} &")
                await asyncio.sleep(2)  # Wait for page to load

            # Remote functions for wikirace - using @sandboxed decorator
            @sandboxed("eval_env")
            def close_all_windows():
                import pywinctl
                windows = pywinctl.getAllWindows()
                for window in windows:
                    try:
                        window.close()
                    except:
                        # Some windows might not be closeable or may have already closed
                        pass

            @sandboxed("eval_env")
            def get_current_wiki_page():
                import pywinctl
                titles = pywinctl.getAllTitles()
                wiki_titles = [title for title in titles if "Wikipedia" in title]
                if wiki_titles:
                    return wiki_titles[0].split(" - Wikipedia")[0]
                return None

            # Wikirace setup
            max_steps = 2
            start_page = "Albert Einstein"
            target_page = "Pizza"
            
            print(f"\nStarting Wikirace: {start_page} → {target_page}")
            
            # Close all windows
            await close_all_windows()
            
            # Open starting page
            await open_wiki(start_page)
            
            # Check current page using decorated function
            current_page = await get_current_wiki_page()
            print(f"Starting page: {current_page}")
            assert current_page == start_page, f"Expected {start_page}, got {current_page}"
            
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
            
            try: 
                async for result in agent.run(prompt):    
                    steps += 1
                    print(f"Step {steps}: {result}")
                    
                    # Check again
                    current_page = await get_current_wiki_page()
                    print(f"Current page: {current_page}")
                    
                    # Check if we reached the target
                    if current_page and target_page.lower() in current_page.lower():
                        success = True
                        print(f"🎉 SUCCESS! Reached {target_page} in {steps} steps!")
                        await agent._loop.cancel()
                        break
                    
                    # Safety check
                    if steps >= max_steps:
                        print(f"❌ Stopping agent: Reached maximum steps ({max_steps})")
                        await agent._loop.cancel()
                        break
            except asyncio.CancelledError:
                print("Agent stopped")
                            
            end_time = time.time()
            duration = end_time - start_time
            await asyncio.sleep(2) # Wait for agent to finish
            
            # Results
            print(f"\n=== WIKIRACE RESULTS ===")
            print(f"Start: {start_page}")
            print(f"Target: {target_page}")
            print(f"Steps taken: {steps}")
            print(f"Success: {success}")
            print(f"Duration: {duration:.2f} seconds")
        finally:
            # Important to clean up resources
            # await computer.stop()
            pass
            
    except Exception as e:
        print(f"Error in main: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())