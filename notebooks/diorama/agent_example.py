import asyncio
from diorama import Diorama
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path("~/cua/.env.local").expanduser())

from agent import AgentLoop, ComputerAgent as Agent, LLM, LLMProvider
from PIL import Image
import rpack

async def make_mosaic(dioramas):
    sizes = []
    for d in dioramas:
        size = await d.interface.get_screen_size()
        sizes.append((size['width'], size['height']))
    positions = rpack.pack(sizes)
    max_x = max(x + w for (x, y), (w, h) in zip(positions, sizes))
    max_y = max(y + h for (x, y), (w, h) in zip(positions, sizes))
    mosaic = Image.new("RGBA", (max_x, max_y), (30, 30, 30, 255))
    draw_positions = positions
    return mosaic, draw_positions

async def main():
    # diorama's are virtual desktops, they allow you to control multiple apps at once
    diorama1 = Diorama.create_from_apps("Safari")
    diorama2 = Diorama.create_from_apps("Notes")
    diorama3 = Diorama.create_from_apps("Calculator")
    diorama4 = Diorama.create_from_apps("Terminal")
    
    # create agents
    agents = [
        diorama1.agent.openai(),
        diorama2.agent.openai(),
        diorama3.agent.openai(),modif
        diorama4.agent.openai()
    ]
    dioramas = [diorama1, diorama2, diorama3, diorama4]
    mosaic, draw_positions = await make_mosaic(dioramas)
    mosaic.save(Path("~/cua/notebooks/app_screenshots/mosaic.png").expanduser())

    tasks = [
        "In Safari, find a cat picture",
        "In Notes, make a note named 'Test' and draw an ASCII dog",
        "In Calculator, add 2 + 2",
        "In Terminal, type 'ls' and press enter"
    ]
    
    async def run_agent(agent, task, diorama_idx):
        diorama = dioramas[diorama_idx]
        
        # start with a screenshot
        screenshot = await diorama.interface.screenshot(as_bytes=False)
        mosaic.paste(screenshot, draw_positions[diorama_idx])
        mosaic.save(Path("~/cua/notebooks/app_screenshots/mosaic.png").expanduser())
        
        async for response in agent.run(task):
            print(response)
            
            # update mosaic
            screenshot = await diorama.interface.screenshot(as_bytes=False)
            mosaic.paste(screenshot, draw_positions[diorama_idx])
            mosaic.save(Path("~/cua/notebooks/app_screenshots/mosaic.png").expanduser())

    # run agents
    await asyncio.gather(*[run_agent(agent, task, idx) for idx, (agent, task) in enumerate(zip(agents, tasks))])
    
if __name__ == "__main__":
    asyncio.run(main())