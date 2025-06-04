import os
import asyncio
import json
import random
from pathlib import Path
import sys
import traceback
import time
from functools import wraps
import urllib.request
import datetime
from urllib.parse import quote

# Global variable to track all results
all_results = []

# Wikirace prompt template
WIKIRACE_PROMPT_TEMPLATE = """
You are playing Wikirace in {browser}! Your goal is to navigate from "{start_page}" to "{target_page}" 
by clicking only on Wikipedia links within articles.

Rules:
1. Only click on links within Wikipedia articles (blue text)
2. No using search, back button, or typing URLs
3. You MAY use cmd+f (or ctrl+f) to find text on the current page
4. Do NOT click any search icon or type into any search box unless it's a browser command
5. Try to find the shortest path possible
6. Current target: {target_page}
7. Do not maximize the window or use any other application
8. Avoid wasting actions by scrolling
9. Try using cmd+f and quickly clicking through relevant links in the page as you have a limited number of steps
10. Stay on the English Wikipedia

Look at the current page and click on a link that might lead you closer to {target_page}.
"""

# Store original print function
_print = print

# Define log file path
project_root = Path(__file__).parent.parent
log_file = project_root / "examples" / "evals" / "eval_appuse_log.txt"
results_file = project_root / "examples" / "evals" / "eval_appuse_results.md"

# Custom print function that also logs to file
def print(*args, **kwargs):
    # Call the original print function
    _print(*args, **kwargs)
    
    # Format the output as a string
    output = " ".join(str(arg) for arg in args)
    if kwargs.get("end") is not None:
        output += kwargs["end"]
    else:
        output += "\n"
    
    # Add timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {output}"
    
    # Append to log file
    with open(log_file, "a") as f:
        f.write(log_entry)

# Load environment variables from .env file
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

articles = []

# Load from file
articles_file = project_root / "examples" / "evals" / "wikipedia_most_linked.txt"
with open(articles_file, "r") as f:
    articles = [line.strip() for line in f]


def get_article_links(article_title):
    """Get all links from a Wikipedia article's content"""
    try:
        # Get the article content
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={quote(article_title)}&prop=links&pllimit=500&format=json"
        
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            
        pages = data.get('query', {}).get('pages', {})
        if not pages:
            return []
        
        # Get the first (and only) page
        page = next(iter(pages.values()))
        links = page.get('links', [])
        
        # Filter links to keep only main namespace articles (no special pages, files, etc.)
        article_links = []
        for link in links:
            title = link.get('title', '')
            # Skip if title contains colons (indicates special pages, files, categories, etc.)
            if ':' not in title and title.isascii() and len(title) < 50:
                article_links.append(title)
        
        return article_links
    
    except Exception as e:
        print(f"Error fetching links for {article_title}: {e}")
        return []

def wikipedia_random_walk(start_article, depth=5):
    """
    Perform a random walk through Wikipedia articles
    
    Args:
        start_article (str): The article title to start from
        depth (int): How many steps to take in the random walk
    
    Returns:
        list: Path of article titles visited during the walk
    """
    path = [start_article]
    current_article = start_article
    
    for step in range(depth):
        print(f"Step {step + 1}: Currently at '{current_article}'")
        
        # Get links from current article
        links = get_article_links(current_article)
        
        if not links:
            print(f"No valid links found in '{current_article}'. Ending walk.")
            break
        
        # Randomly select next article
        next_article = random.choice(links)
        path.append(next_article)
        current_article = next_article
        
        print(f"  -> Moving to '{next_article}'")
    
    return path

def get_article_pair(depth=5):
    global articles
    start_article = random.choice(articles)
    target_article = wikipedia_random_walk(start_article, depth)[-1]
    while target_article == start_article:
        start_article = random.choice(articles)
        target_article = wikipedia_random_walk(start_article, depth)[-1]
    return start_article, target_article


def save_results_to_markdown():
    """Save all results to a markdown table"""
    global all_results
    
    if not all_results:
        print("No results to save")
        return
    
    # Create header for the markdown table
    header = "| Timestamp | Scenario | App-Use | Browser | Config | Start | Target | Steps | Success | Duration (s) |"
    separator = "|---|---|---|---|---|---|---|---|---|---|"
    
    # Create rows for each result
    rows = []
    for result in all_results:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = f"| {timestamp} | {result['scenario']} | {result['app_use']} | {result['browser']} | {result['config']} | {result['start']} | {result['target']} | {result['steps']} | {result['success']} | {result['duration']:.2f} |"
        rows.append(row)
    
    # Combine header, separator, and rows
    table = "\n".join([header, separator] + rows)
    
    # Write to file (append mode)
    with open(results_file, "a") as f:
        f.write(f"\n\n## Results Update - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(table)
    
    print(f"Results saved to {results_file}")

async def run_scenario(scenario_name, use_app_use, agent_configs, max_steps=30):
    """Run a specific evaluation scenario"""
    
    print(f"\n=== Running Scenario: {scenario_name} (App-Use: {use_app_use}) ===")
    
    # Create computer instance with or without app-use experiment
    experiments = ["app-use"] if use_app_use else []
    computer = Computer(experiments=experiments)
    
    try:
        # Run the computer
        await computer.run()
        
        # Install required packages
        await computer.venv_install("eval_env", ["pywinctl", "selenium", "beautifulsoup4"])
        
        # Run the specific scenario
        if scenario_name == "messy_desktop":
            await run_messy_desktop_scenario(computer, agent_configs, max_steps)
        elif scenario_name == "parallel_agents":
            await run_parallel_agents_scenario(computer, agent_configs, max_steps)
        else:
            print(f"Unknown scenario: {scenario_name}")
    
    except Exception as e:
        print(f"Error in scenario {scenario_name}: {e}")
        traceback.print_exc()
    finally:
        # Important to clean up resources
        # await computer.stop()
        pass


@sandboxed("eval_env")
def close_all_windows():
    """Close all open windows"""
    import pywinctl
    windows = pywinctl.getAllWindows()
    for window in windows:
        try:
            window.close()
        except:
            # Some windows might not be closeable or may have already closed
            pass


@sandboxed("eval_env")
def get_current_wiki_page(app_name=None):
    """Get the title of the current Wikipedia page
    
    Args:
        app_name: Optional name of the app to check (e.g., 'Safari', 'Firefox')
    """
    import pywinctl
    windows = pywinctl.getAllWindows()
    
    # Filter windows by app name if provided
    if app_name:
        windows = [w for w in windows if w.getAppName() and app_name.lower() in w.getAppName().lower()]
    
    # Get titles from filtered windows
    titles = [w.title for w in windows if w.title]
    wiki_titles = [title for title in titles if "Wikipedia" in title]
    
    if wiki_titles:
        return wiki_titles[0].split(" - Wikipedia")[0]
    return None


@sandboxed("eval_env")
def get_open_app_names():
    """Get names of all open applications"""
    import pywinctl
    windows = pywinctl.getAllWindows()
    return [window.getAppName() for window in windows if window.getAppName()]

def _computer():
    """Get the default computer instance"""
    from computer.helpers import _default_computer
    return _default_computer

async def open_app(app_name):
    """Open a specific application"""
    await _computer().interface.run_command(f"open -a '{app_name}'")
    await asyncio.sleep(2)  # Wait for app to open


async def open_wiki(page, app_name="Safari"):
    """Open a specific Wikipedia page"""
    await _computer().interface.run_command(f"open -a {app_name} https://en.wikipedia.org/wiki/{page.replace(' ', '_')}")
    await asyncio.sleep(2)  # Wait for page to load


async def run_messy_desktop_scenario(computer, agent_configs, max_steps):
    global all_results
    """Run the messy desktop scenario with a single agent"""
    # Get popular wiki articles
    global articles
    start_page, target_page = get_article_pair(depth=1)
    
    print(f"Wiki race: {start_page} → {target_page}")
    
    # Close all windows first
    await close_all_windows()
    
    # Open starting Wikipedia page
    await open_wiki(start_page)
    
    # Open 3 random apps to create a messy desktop
    apps_to_open = ["Notes", "Terminal", "System Settings"]
    for app in apps_to_open:
        await open_app(app)
    
    # Verify apps are open
    open_apps = await get_open_app_names()
    print(f"Open applications: {open_apps}")
    
    # Create the agent's computer interface
    # If app-use is enabled, create a desktop limited to Safari/Firefox
    if "app-use" in (computer.experiments or []):
        browser_desktop = computer.create_desktop_from_apps(["Safari"])
        agent_computer = browser_desktop
    else:
        agent_computer = computer
    
    # Run each agent configuration
    for config_name, loop_provider, model_provider in agent_configs:
        print(f"\n--- Testing Agent: {config_name} ---")
        
        # Create agent with the specified configuration
        agent = ComputerAgent(
            computer=agent_computer,
            loop=loop_provider,
            model=LLM(model_provider) if not isinstance(model_provider, LLM) else model_provider,
            trajectory_dir="examples/evals/trajectories/eval_appuse"
        )
        
        # Run the wikirace
        steps = 0
        success = False
        start_time = time.time()
        
        # Use the template with formatting for this scenario
        prompt = WIKIRACE_PROMPT_TEMPLATE.format(
            browser="Safari",
            start_page=start_page,
            target_page=target_page
        )
        
        try:
            while steps < max_steps and not success: 
                async for result in agent.run(prompt):    
                    steps += 1
                    print(f"Step {steps}")
                    
                    def process_result():
                        if result.get("content"):
                            print(f"Agent: {result.get('content', '')}")

                        else:
                            outputs = result.get("output", [])
                            for output in outputs:
                                if output.get("type") == "message":
                                    content = output.get("content", [])
                                    for content_part in content:
                                        if content_part.get("text"):
                                            print(f"Agent: {content_part.get('text', '')}")

                                elif output.get("type") == "reasoning":
                                    # if it's openAI, we only have access to a summary of the reasoning
                                    summary_content = output.get("summary", [])
                                    if summary_content:
                                        for summary_part in summary_content:
                                            if summary_part.get("type") == "summary_text":
                                                print(f"Agent: {summary_part.get('text', '')}")

                                    else:
                                        summary_content = output.get("text", "")
                                        if summary_content:
                                            print(f"Agent: {summary_content}")

                                elif output.get("type") == "computer_call":
                                    action = output.get("action", {})
                                    action_type = action.get("type", "")
                                    if action_type:
                                        action_title = f"🛠️ Performing {action_type}"
                                        if action.get("x") and action.get("y"):
                                            action_title += f" at ({action['x']}, {action['y']})"
                                        print(f"Agent: {action_title}\n```json\n{json.dumps(action)}\n```")

                    
                    # Process and print the result
                    process_result()
                    
                    # Check current page
                    current_page = await get_current_wiki_page("Safari")
                    print(f"Current page: {current_page}")
                    print(f"Target: {target_page}")
                    
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
        await asyncio.sleep(2)  # Wait for agent to finish
        
        # Results
        print(f"\n=== WIKIRACE RESULTS: {config_name} ===")
        print(f"App-Use Enabled: {'Yes' if 'app-use' in (computer.experiments or []) else 'No'}")
        print(f"Start: {start_page}")
        print(f"Target: {target_page}")
        print(f"Steps taken: {steps}")
        print(f"Success: {success}")
        print(f"Duration: {duration:.2f} seconds")


async def run_parallel_agents_scenario(computer, agent_configs, max_steps):
    global all_results
    
    """Run two agents in parallel, one using Safari and one using Firefox"""
    # Get popular wiki articles
    global articles
    safari_start, safari_target = get_article_pair(depth=1)
    firefox_start, firefox_target = get_article_pair(depth=1)
    
    print(f"Safari Wiki race: {safari_start} → {safari_target}")
    print(f"Firefox Wiki race: {firefox_start} → {firefox_target}")
    
    # Close all windows first
    await close_all_windows()
    
    # Open Safari with starting page
    await open_wiki(safari_start, "Safari")
    await asyncio.sleep(2)
    
    # Open Firefox with starting page
    await open_wiki(firefox_start, "Firefox")
    await asyncio.sleep(2)
    
    # Create agent configurations
    for config_name, loop_provider, model_provider in agent_configs:
        print(f"\n--- Testing Parallel Agents: {config_name} ---")
        
        # Create the agent interfaces
        if "app-use" in (computer.experiments or []):
            safari_desktop = computer.create_desktop_from_apps(["Safari"])
            firefox_desktop = computer.create_desktop_from_apps(["Firefox"])
        else:
            safari_desktop = computer
            firefox_desktop = computer
        
        # Save screenshots
        screenshot_dir = project_root / "examples" / "evals" / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)
        safari_screenshot_path = screenshot_dir / f"safari_{config_name}.png"
        firefox_screenshot_path = screenshot_dir / f"firefox_{config_name}.png"
        screenshot_bytes = await safari_desktop.interface.screenshot()
        with open(safari_screenshot_path, "wb") as f:
            f.write(screenshot_bytes)
        screenshot_bytes = await firefox_desktop.interface.screenshot()
        with open(firefox_screenshot_path, "wb") as f:
            f.write(screenshot_bytes)
        
        # Create agents
        safari_agent = ComputerAgent(
            computer=safari_desktop,
            loop=loop_provider,
            model=LLM(model_provider) if not isinstance(model_provider, LLM) else model_provider,
            trajectory_dir="examples/evals/trajectories/eval_parallel_safari"
        )
        
        firefox_agent = ComputerAgent(
            computer=firefox_desktop,
            loop=loop_provider,
            model=LLM(model_provider) if not isinstance(model_provider, LLM) else model_provider,
            trajectory_dir="examples/evals/trajectories/eval_parallel_firefox"
        )
        
        # Create prompts using the template
        safari_prompt = WIKIRACE_PROMPT_TEMPLATE.format(
            browser="Safari",
            start_page=safari_start,
            target_page=safari_target
        )
        
        firefox_prompt = WIKIRACE_PROMPT_TEMPLATE.format(
            browser="Firefox",
            start_page=firefox_start,
            target_page=firefox_target
        )
        
        # Track results
        safari_results = {
            "steps": 0,
            "success": False,
            "start_time": time.time(),
            "end_time": None
        }
        
        firefox_results = {
            "steps": 0,
            "success": False,
            "start_time": time.time(),
            "end_time": None
        }
        
        # Function to run a single agent
        async def run_agent(agent, prompt, browser, start_page, target_page, results):
            try:
                while results["steps"] < max_steps and not results["success"]:
                    async for result in agent.run(prompt):
                        results["steps"] += 1
                        print(f"{browser} Step {results['steps']}")
                        
                        def process_result():
                            if result.get("content"):
                                print(f"{browser} Agent: {result.get('content', '')}")

                            else:
                                outputs = result.get("output", [])
                                for output in outputs:
                                    if output.get("type") == "message":
                                        content = output.get("content", [])
                                        for content_part in content:
                                            if content_part.get("text"):
                                                print(f"{browser} Agent: {content_part.get('text', '')}")

                                    elif output.get("type") == "reasoning":
                                        # if it's openAI, we only have access to a summary of the reasoning
                                        summary_content = output.get("summary", [])
                                        if summary_content:
                                            for summary_part in summary_content:
                                                if summary_part.get("type") == "summary_text":
                                                    print(f"{browser} Agent: {summary_part.get('text', '')}")

                                        else:
                                            summary_content = output.get("text", "")
                                            if summary_content:
                                                print(f"{browser} Agent: {summary_content}")

                                    elif output.get("type") == "computer_call":
                                        action = output.get("action", {})
                                        action_type = action.get("type", "")
                                        if action_type:
                                            action_title = f"🛠️ Performing {action_type}"
                                            if action.get("x") and action.get("y"):
                                                action_title += f" at ({action['x']}, {action['y']})"
                                            print(f"{browser} Agent: {action_title}\n```json\n{json.dumps(action)}\n```")

                        
                        # Process and print the result
                        process_result()
                        
                        # Check current page
                        current_page = await get_current_wiki_page(browser)
                        print(f"{browser} current page: {current_page}")
                        print(f"{browser} target: {target_page}") 
                        
                        # Add result to global tracking
                        global all_results
                        current_result = {
                            'scenario': 'parallel_agents',
                            'app_use': 'Yes' if 'app-use' in (computer.experiments or []) else 'No',
                            'browser': browser,
                            'config': config_name,
                            'start': start_page,
                            'target': target_page,
                            'steps': results['steps'],
                            'success': results['success'],
                            'duration': time.time() - results['start_time']
                        }
                        all_results.append(current_result)
                        
                        # Save results after each step
                        save_results_to_markdown()
                        
                        # Check if we reached the target
                        if current_page and target_page.lower() in current_page.lower():
                            results["success"] = True
                            print(f"🎉 {browser} SUCCESS! Reached {target_page} in {results['steps']} steps!")
                            await agent._loop.cancel()
                            break
                        
                        # Check if we reached the maximum steps
                        if results["steps"] >= max_steps:
                            print(f"❌ Stopping {browser} agent: Reached maximum steps ({max_steps})")
                            await agent._loop.cancel()
                            break
            except asyncio.CancelledError:
                print(f"{browser} agent stopped")
            finally:
                results["end_time"] = time.time()
        
        # Run both agents in parallel
        await asyncio.gather(
            run_agent(safari_agent, safari_prompt, "Safari", safari_start, safari_target, safari_results),
            run_agent(firefox_agent, firefox_prompt, "Firefox", firefox_start, firefox_target, firefox_results)
        )
        
        # Wait for agents to finish
        await asyncio.sleep(2)
        
        # Print results
        print(f"\n=== PARALLEL AGENTS RESULTS: {config_name} ===")
        print(f"App-Use Enabled: {'Yes' if 'app-use' in (computer.experiments or []) else 'No'}")
        
        print(f"\nSafari Results:")
        print(f"Start: {safari_start}")
        print(f"Target: {safari_target}")
        print(f"Steps taken: {safari_results['steps']}")
        print(f"Success: {safari_results['success']}")
        print(f"Duration: {safari_results['end_time'] - safari_results['start_time']:.2f} seconds")
        
        print(f"\nFirefox Results:")
        print(f"Start: {firefox_start}")
        print(f"Target: {firefox_target}")
        print(f"Steps taken: {firefox_results['steps']}")
        print(f"Success: {firefox_results['success']}")
        print(f"Duration: {firefox_results['end_time'] - firefox_results['start_time']:.2f} seconds")


async def main():
    try:
        
        # Define agent configurations to test
        agent_configs = [
            # ("OpenAI", AgentLoop.OPENAI, LLMProvider.OPENAI),
            # ("Anthropic", AgentLoop.ANTHROPIC, LLMProvider.ANTHROPIC),
            ("UITARS", AgentLoop.UITARS, LLM(LLMProvider.OAICOMPAT, name="tgi", provider_base_url=os.getenv("UITARS_BASE_URL")))
        ]
        
        # # Run the test scenario without any agents
        # print("Running test scenario for sandboxed functions")
        # await run_test_scenario()
        
        # Set maximum steps for each agent run
        max_steps = 15
        runs = 5

        # run all scenarios
        for _ in range(runs):
            # Scenario 1: Messy desktop without App-Use
            await run_scenario("messy_desktop", False, agent_configs, max_steps)
            
            # Scenario 1: Messy desktop with App-Use
            await run_scenario("messy_desktop", True, agent_configs, max_steps)
            
            # Scenario 2: Parallel agents without App-Use
            await run_scenario("parallel_agents", False, agent_configs, max_steps)
            
            # Scenario 2: Parallel agents with App-Use
            await run_scenario("parallel_agents", True, agent_configs, max_steps)
            
    except Exception as e:
        print(f"Error in main: {e}")
        traceback.print_exc()


async def run_test_scenario(max_iterations=5):
    """Test sandboxed functions by opening the same pages in Safari and Firefox and checking if they match
    
    This function opens the same Wikipedia pages in both browsers and verifies that
    the get_current_wiki_page function returns the same result for both browsers.
    It does this for the specified number of iterations.
    """
    
    # Create computer instance
    computer = Computer()
    await computer.run()
    
    # Get popular wiki articles
    global articles
    selected_articles = random.sample(articles, max_iterations)
    
    print(f"\n--- Running Test Scenario for {max_iterations} iterations ---")
    
    # Close all windows first
    await close_all_windows()
    
    # Open both browsers
    await open_app("Safari")
    await open_app("Firefox")
    
    # Verify browsers are open
    open_apps = await get_open_app_names()
    print(f"Open applications: {open_apps}")
    
    # Run test iterations
    for i, article in enumerate(selected_articles):
        print(f"\nIteration {i+1}/{max_iterations}: Testing with article '{article}'")
        
        # Open the same Wikipedia page in both browsers
        await open_wiki(article, "Safari")
        await open_wiki(article, "Firefox")
        await asyncio.sleep(3)  # Give a bit more time for both pages to load
        
        # Check if both browsers show the same page
        safari_page = await get_current_wiki_page("Safari")
        firefox_page = await get_current_wiki_page("Firefox")
        
        print(f"Safari page: {safari_page}")
        print(f"Firefox page: {firefox_page}")
        
        if safari_page == firefox_page:
            print(f"✅ MATCH: Both browsers show '{safari_page}'")
        else:
            print(f"❌ MISMATCH: Safari shows '{safari_page}', Firefox shows '{firefox_page}'")
        
        await asyncio.sleep(1)  # Brief pause between iterations
    
    print("\n--- Test Scenario Completed ---")


if __name__ == "__main__":
    asyncio.run(main())
