#!/usr/bin/env python3
"""Diorama: A virtual desktop manager for macOS"""

import os
import asyncio
import logging
import sys
import io
from typing import Union
from PIL import Image

from draw import capture_all_apps, AppActivationContext, get_frontmost_and_active_app, get_all_windows, get_running_apps

from diorama_computer import DioramaComputer
from computer_server.handlers.macos import *
from agent import ComputerAgent, LLM, LLMProvider, AgentLoop

# simple, nicely formatted logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger("diorama.virtual_desktop")

automation_handler = MacOSAutomationHandler()

class AgentFactory:
    def __init__(self, diorama):
        self.diorama = diorama
    
    def create_agent(self, loop: AgentLoop, model: LLM):
        return ComputerAgent(
            computer=self.diorama.computer,
            loop=loop,
            model=model
        )
    
    def openai(self):
        return self.create_agent(AgentLoop.OPENAI, LLM(
            provider=LLMProvider.OPENAI,
            name="computer-use-preview"
        ))
    
    def anthropic(self):
        return self.create_agent(AgentLoop.ANTHROPIC, LLM(
            provider=LLMProvider.ANTHROPIC,
        ))
        
    def openai_omni(self, model_name):
        return self.create_agent(AgentLoop.OMNI, LLM(
            provider=LLMProvider.OPENAI,
            name=model_name
        ))
        
    def uitars(self):
        return self.create_agent(AgentLoop.UITARS, LLM(
            provider=LLMProvider.OAICOMPAT,
            name="tgi",
            provider_base_url=os.getenv("UITARS_BASE_URL")
        ))

class Diorama:
    _scheduler_queue = None
    _scheduler_task = None
    _loop = None
    _scheduler_started = False

    @classmethod
    def create_from_apps(cls, *args) -> DioramaComputer:
        cls._ensure_scheduler()
        return cls(args).computer

    def __init__(self, app_list):
        self.app_list = app_list
        self.agent = AgentFactory(self)
        self.interface = self.Interface(self)
        self.computer = DioramaComputer(self)
        self.focus_context = None

    @classmethod
    def _ensure_scheduler(cls):
        if not cls._scheduler_started:
            logger.info("Starting Diorama scheduler loop…")
            cls._scheduler_queue = asyncio.Queue()
            cls._loop = asyncio.get_event_loop()
            cls._scheduler_task = cls._loop.create_task(cls._scheduler_loop())
            cls._scheduler_started = True

    @classmethod
    async def _scheduler_loop(cls):
        while True:
            cmd = await cls._scheduler_queue.get()
            action = cmd.get("action")
            args = cmd.get("arguments", {})
            future = cmd.get("future")
            logger.info(f"Processing command: {action} | args={args}")
            
            app_whitelist = args.get("app_list", [])
            
            all_windows = get_all_windows()
            running_apps = get_running_apps()
            frontmost_app, active_app_to_use, active_app_pid = get_frontmost_and_active_app(all_windows, running_apps, app_whitelist)
            focus_context = AppActivationContext(active_app_pid, active_app_to_use, logger)
            
            with focus_context:
                try:
                    if action == "screenshot":
                        app_whitelist = list(args["app_list"]) + ["Window Server", "Dock"]
                        logger.info(f"Taking screenshot for apps: {app_whitelist}")
                        result, img = capture_all_apps(
                            app_whitelist=app_whitelist,
                            save_to_disk=False,
                            take_focus=False
                        )
                        logger.info("Screenshot complete.")
                        if future:
                            future.set_result((result, img))
                    # Mouse actions
                    elif action in ["left_click", "right_click", "double_click", "move_cursor", "drag_to"]:
                        x = args.get("x")
                        y = args.get("y")
                        duration = args.get("duration", 0.5)
                        if action == "left_click":
                            await automation_handler.left_click(x, y)
                        elif action == "right_click":
                            await automation_handler.right_click(x, y)
                        elif action == "double_click":
                            await automation_handler.double_click(x, y)
                        elif action == "move_cursor":
                            await automation_handler.move_cursor(x, y)
                        elif action == "drag_to":
                            await automation_handler.drag_to(x, y, duration=duration)
                        if future:
                            future.set_result(None)
                    # Keyboard actions
                    elif action == "type_text":
                        text = args.get("text")
                        await automation_handler.type_text(text)
                        if future:
                            future.set_result(None)
                    elif action == "press_key":
                        key = args.get("key")
                        await automation_handler.press_key(key)
                        if future:
                            future.set_result(None)
                    elif action == "hotkey":
                        keys = args.get("keys", [])
                        await automation_handler.hotkey(keys)
                        if future:
                            future.set_result(None)
                    elif action == "get_cursor_position":
                        pos = await automation_handler.get_cursor_position()
                        if future:
                            future.set_result(pos)
                    else:
                        logger.warning(f"Unknown action: {action}")
                        if future:
                            future.set_exception(ValueError(f"Unknown action: {action}"))
                except Exception as e:
                    logger.error(f"Exception during {action}: {e}", exc_info=True)
                    if future:
                        future.set_exception(e)

    class Interface():
        def __init__(self, diorama):
            self._diorama = diorama
            
            self._scene_hitboxes = []
            self._scene_size = None

        async def _send_cmd(self, action, arguments=None):
            Diorama._ensure_scheduler()
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            logger.info(f"Enqueuing {action} command for apps: {self._diorama.app_list}")
            await Diorama._scheduler_queue.put({
                "action": action,
                "arguments": {"app_list": self._diorama.app_list, **(arguments or {})},
                "future": future
            })
            return await future

        async def screenshot(self, as_bytes: bool = True) -> Union[bytes, Image]:
            result, img = await self._send_cmd("screenshot")
            self._scene_hitboxes = result.get("hitboxes", [])
            self._scene_size = img.size
            
            if as_bytes:
                # PIL Image to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format="PNG")
                img_byte_arr = img_byte_arr.getvalue()
                return img_byte_arr
            else:
                return img

        async def left_click(self, x, y):
            sx, sy = await self.to_screen_coordinates(x, y)
            await self._send_cmd("left_click", {"x": sx, "y": sy})

        async def right_click(self, x, y):
            sx, sy = await self.to_screen_coordinates(x, y)
            await self._send_cmd("right_click", {"x": sx, "y": sy})

        async def double_click(self, x, y):
            sx, sy = await self.to_screen_coordinates(x, y)
            await self._send_cmd("double_click", {"x": sx, "y": sy})

        async def move_cursor(self, x, y):
            sx, sy = await self.to_screen_coordinates(x, y)
            await self._send_cmd("move_cursor", {"x": sx, "y": sy})

        async def drag_to(self, x, y, duration=0.5):
            sx, sy = await self.to_screen_coordinates(x, y)
            await self._send_cmd("drag_to", {"x": sx, "y": sy, "duration": duration})

        async def get_cursor_position(self):
            return await self._send_cmd("get_cursor_position")

        async def type_text(self, text):
            await self._send_cmd("type_text", {"text": text})

        async def press_key(self, key):
            await self._send_cmd("press_key", {"key": key})

        async def hotkey(self, *keys):
            await self._send_cmd("hotkey", {"keys": list(keys)})

        async def get_screen_size(self) -> dict[str, int]:
            if not self._scene_size:
                await self.screenshot()
            return { "width": self._scene_size[0], "height": self._scene_size[1] }

        async def to_screen_coordinates(self, x: float, y: float) -> tuple[float, float]:
            """Convert screenshot coordinates to screen coordinates.

            Args:
                x: X absolute coordinate in screenshot space
                y: Y absolute coordinate in screenshot space

            Returns:
                tuple[float, float]: (x, y) absolute coordinates in screen space
            """
            if not self._scene_hitboxes:
                await self.screenshot() # get hitboxes
            # Try all hitboxes
            for h in self._scene_hitboxes:
                rect = h.get("hitbox")
                if not rect or len(rect) != 4:
                    continue
                x0, y0, x1, y1 = rect
                width = x1 - x0
                height = y1 - y0
                abs_x = x0 + x * width
                abs_y = y0 + y * height
                # Check if (abs_x, abs_y) is inside this hitbox
                if x0 <= abs_x <= x1 and y0 <= abs_y <= y1:
                    return abs_x, abs_y
            return x, y

        async def to_screenshot_coordinates(self, x: float, y: float) -> tuple[float, float]:
            """Convert screen coordinates to screenshot coordinates.

            Args:
                x: X absolute coordinate in screen space
                y: Y absolute coordinate in screen space

            Returns:
                tuple[float, float]: (x, y) absolute coordinates in screenshot space
            """
            if not self._scene_hitboxes:
                await self.screenshot() # get hitboxes
            for h in self._scene_hitboxes:
                rect = h.get("target")
                if not rect or len(rect) != 4:
                    continue
                x0, y0, x1, y1 = rect
                width = x1 - x0
                height = y1 - y0
                if x0 <= x <= x1 and y0 <= y <= y1:
                    rel_x = (x - x0) / width if width else 0.0
                    rel_y = (y - y0) / height if height else 0.0
                    return rel_x, rel_y
            return x, y

async def main():
    from PIL import Image, ImageDraw
    from draw import capture_all_apps

    desktop1 = Diorama.create_from_apps(["Discord", "Notes"])
    desktop2 = Diorama.create_from_apps(["Terminal"])

    img1 = await desktop1.interface.screenshot(as_bytes=False)
    img2 = await desktop2.interface.screenshot(as_bytes=False)

    img1.save("app_screenshots/desktop1.png")
    img2.save("app_screenshots/desktop2.png")


if __name__ == "__main__":
    asyncio.run(main())
