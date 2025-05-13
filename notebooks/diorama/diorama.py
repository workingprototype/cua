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
            self.hitboxes = []

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
            result, img = await future
            # Store hitboxes after screenshot
            self.hitboxes = result.get("hitboxes", [])
            return result, img

        async def to_screen_coordinates(self, x: float, y: float) -> tuple[float, float]:
            """
            Convert screenshot-relative coordinates (x, y) to absolute screen coordinates.
            Find the first hitbox whose 'hitbox' contains the mapped (abs_x, abs_y).
            If none found, return input.
            """
            if not self.hitboxes:
                await self.screenshot() # get hitboxes
            # Try all hitboxes
            for h in self.hitboxes:
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
            """
            Convert absolute screen coordinates (x, y) to screenshot-relative coordinates (normalized to [0, 1]).
            Find the first hitbox whose 'target' contains (x, y).
            If none found, return input.
            """
            if not self.hitboxes:
                await self.screenshot() # get hitboxes
            for h in self.hitboxes:
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

    # Take full screen screenshot (no app whitelist)
    result_full, img_full = capture_all_apps()
    # Take desktop1 screenshot
    result1, img1 = await desktop1.interface.screenshot()

    # Pick a sample normalized screenshot coordinate
    test_screenshot_coord = (0.5, 0.5)  # center
    # Convert to screen coordinates using desktop1 (should map to full screenshot)
    screen_coord = await desktop1.interface.to_screen_coordinates(*test_screenshot_coord)
    # Convert back to screenshot coordinates on desktop1
    screenshot_coord_back = await desktop1.interface.to_screenshot_coordinates(*screen_coord)

    # Draw on full screenshot: the mapped screen coordinate
    img_full = img_full.convert("RGBA")
    img1 = img1.convert("RGBA")
    width_full, height_full = img_full.size
    width1, height1 = img1.size
    x_screen, y_screen = int(screen_coord[0]), int(screen_coord[1])
    x1, y1 = int(screenshot_coord_back[0] * width1), int(screenshot_coord_back[1] * height1)

    draw_full = ImageDraw.Draw(img_full)
    r = 12
    draw_full.ellipse([(x_screen - r, y_screen - r), (x_screen + r, y_screen + r)], fill=(255,0,0,200), outline=(0,0,0,255))
    draw_full.text((x_screen + r, y_screen), "screen coord", fill=(255,0,0,255))

    draw1 = ImageDraw.Draw(img1)
    draw1.ellipse([(x1 - r, y1 - r), (x1 + r, y1 + r)], fill=(0,0,255,200), outline=(0,0,0,255))
    draw1.text((x1 + r, y1), f"screenshot coord", fill=(0,0,255,255))

    # Create a new image side by side
    total_width = img_full.width + img1.width
    max_height = max(img_full.height, img1.height)
    combined = Image.new("RGBA", (total_width, max_height), (255,255,255,255))
    combined.paste(img_full, (0, 0))
    combined.paste(img1, (img_full.width, 0))

    # Draw an arrow from the point in img_full to the point in img1
    arrow_draw = ImageDraw.Draw(combined)
    start = (x_screen, y_screen)
    end = (x1 + img_full.width, y1)
    arrow_draw.line([start, end], fill=(0,128,0,255), width=3)
    # Arrowhead
    def draw_arrowhead(draw, start, end, color, size=15):
        import math
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        for a in [math.pi/8, -math.pi/8]:
            x = end[0] - size * math.cos(angle + a)
            y = end[1] - size * math.sin(angle + a)
            draw.line([end, (x, y)], fill=color, width=3)
    draw_arrowhead(arrow_draw, start, end, (0,128,0,255))

    combined.save("coord_mapping_demo.png")
    print("Saved coordinate mapping demo to coord_mapping_demo.png")

if __name__ == "__main__":
    asyncio.run(main())
