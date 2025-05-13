#!/usr/bin/env python3
"""Diorama: A virtual desktop manager for macOS"""

import asyncio
import logging
import sys

from draw import capture_all_apps

# simple, nicely formatted logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger("diorama.virtual_desktop")

class Diorama:
    _scheduler_queue = None
    _scheduler_task = None
    _loop = None
    _scheduler_started = False

    def __init__(self, app_list):
        self.app_list = app_list
        self.interface = self.Interface(self)

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
            if action == "screenshot":
                try:
                    app_whitelist = list(args["app_list"]) + ["Window Server", "Dock"]
                    logger.info(f"Taking screenshot for apps: {app_whitelist}")
                    result, img = capture_all_apps(
                        save_to_disk=args.get("save_to_disk", False),
                        app_whitelist=app_whitelist,
                        output_dir=args.get("output_dir"),
                        take_focus=args.get("take_focus", True)
                    )
                    logger.info("Screenshot complete.")
                    if future:
                        future.set_result((result, img))
                except Exception as e:
                    logger.error(f"Exception during screenshot: {e}", exc_info=True)
                    if future:
                        future.set_exception(e)
            else:
                logger.warning(f"Unknown action: {action}")
                if future:
                    future.set_exception(ValueError(f"Unknown action: {action}"))

    @classmethod
    def create_from_apps(cls, app_list):
        cls._ensure_scheduler()
        return cls(app_list)

    class Interface:
        def __init__(self, diorama):
            self._diorama = diorama

        async def screenshot(self, save_to_disk=False, output_dir=None, take_focus=True):
            Diorama._ensure_scheduler()
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            logger.info(f"Enqueuing screenshot command for apps: {self._diorama.app_list}")
            await Diorama._scheduler_queue.put({
                "action": "screenshot",
                "arguments": {
                    "app_list": self._diorama.app_list,
                    "save_to_disk": save_to_disk,
                    "output_dir": output_dir,
                    "take_focus": take_focus
                },
                "future": future
            })
            return await future

async def main():
    desktop1 = Diorama.create_from_apps(["Discord", "Notes"])
    desktop2 = Diorama.create_from_apps(["Google Chrome"])
    await desktop1.interface.screenshot()
    await desktop2.interface.screenshot()
    
if __name__ == "__main__":
    asyncio.run(main())
