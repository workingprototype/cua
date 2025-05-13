import asyncio
from diorama import Diorama
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path("~/cua/.env.local").expanduser())

from agent import AgentLoop, ComputerAgent as Agent, LLM, LLMProvider

async def main():
    # diorama's are virtual desktops, they allow you to control multiple apps at once
    diorama1 = Diorama.create_from_apps("Terminal")
    diorama2 = Diorama.create_from_apps("Notes")
    diorama3 = Diorama.create_from_apps("Safari")
    diorama4 = Diorama.create_from_apps("Calendar")
    
    
    agents = [
        Agent(
            computer=diorama1, 
            model=LLM("openai", "computer-use-preview"), 
            loop=AgentLoop.OPENAI
        ),
        Agent(diorama2, LLM("anthropic", "claude-3-7-sonnet-20250219"), AgentLoop.ANTHROPIC),
        Agent(diorama3, LLM("openai", "gpt-4.1-nano"), AgentLoop.OMNI),
        Agent(diorama4, LLM("oaicompat", "tgi", os.getenv("UITARS_BASE_URL")), AgentLoop.UITARS)
    ]
    
    tasks = [
        "In Terminal, run 'echo Hello World'",
        "In Notes, create a new note with the title 'Test' and the content 'This is a test note.'",
        "In Safari, go to https://www.google.com",
        "In Calendar, create a new event with the title 'Test' and the content 'This is a test event.'"
    ]
    
    async for response in asyncio.gather(*[agent.run(task) for agent, task in zip(agents, tasks)]):
        print(response)
    

if __name__ == "__main__":
    asyncio.run(main())