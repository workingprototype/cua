#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path
import datasets
from PIL import Image
import imageio
import io

# Helper to extract screenshots from computer_call

def extract_screenshot_hash(screenshot_str):
    import re
    match = re.search(r'<Screenshot: MD5 ([a-f0-9]+):([0-9]+)>', screenshot_str)
    if match:
        return match.group(1), int(match.group(2))
    return None, None

def process_dataset(dataset_path, output_json=None, gif_dir=None):
    dataset = datasets.load_from_disk(dataset_path)
    gif_dir = Path(gif_dir or (Path(__file__).parent.parent / "src/assets/gifs"))
    gif_dir.mkdir(parents=True, exist_ok=True)
    output = []

    # Group turns by user messages
    turns = []
    for example in dataset:
        tool_calls_str = example.get("tool_calls")
        images = example.get("images", [])
        if not tool_calls_str:
            continue
        tool_calls = json.loads(tool_calls_str)
        turns.append({"tool_calls": tool_calls, "images": images})

    # Now, for each user message, collect screenshots until next user message
    gif_idx = 0
    for t_idx, turn in enumerate(turns):
        tool_calls = turn["tool_calls"]
        images = turn["images"]
        screenshots = []
        prompt = None
        i = 0
        while i < len(tool_calls):
            call = tool_calls[i]
            # User message
            if call["name"] == "message" and call.get("role", "user") == "user":
                # Start a new node
                prompt = json.loads(call["arguments"]).get("text", "")
                screenshots = []
                i += 1
                # Collect screenshots until next user message
                while i < len(tool_calls):
                    next_call = tool_calls[i]
                    if next_call["name"] == "message" and next_call.get("role", "user") == "user":
                        break
                    screenshot_str = next_call.get("result", {}).get("screenshot")
                    if screenshot_str:
                        hash_val, idx = extract_screenshot_hash(screenshot_str)
                        if hash_val is not None and idx is not None and idx < len(images):
                                img = images[idx]
                                # Convert PIL.Image to bytes for imageio
                                buf = io.BytesIO()
                                img.save(buf, format="PNG")
                                buf.seek(0)
                                screenshots.append(Image.open(buf).convert("RGBA"))
                    i += 1
                print(f"Found {len(screenshots)} screenshots for node {prompt}")
                # Make GIF if screenshots found
                gif_path = None
                if screenshots:
                    gif_name = f"msg_{gif_idx:03d}.gif"
                    gif_path = gif_dir / gif_name
                    imageio.mimsave(gif_path, screenshots, format="GIF", duration=0.8)
                    gif_idx += 1
                # Collect tool call names for this node (excluding user messages)
                tool_calls_list = []
                screenshot_map = {}  # Map screenshot hashes to their indices
                
                # Find the start index (after current user message) and end index (before next user message)
                start_idx = None
                end_idx = len(tool_calls)
                
                # Find the current user message index
                for call_idx in range(len(tool_calls)):
                    call = tool_calls[call_idx]
                    if call["name"] == "message" and call.get("role", "user") == "user":
                        if json.loads(call["arguments"]).get("text", "") == prompt:
                            start_idx = call_idx + 1  # Start after this user message
                            break
                
                # Find the next user message index
                if start_idx is not None:
                    for call_idx in range(start_idx, len(tool_calls)):
                        call = tool_calls[call_idx]
                        if call["name"] == "message" and call.get("role", "user") == "user":
                            end_idx = call_idx  # End before next user message
                            break
                
                # Build screenshot map for this range only
                for call_idx in range(start_idx or 0, end_idx):
                    call = tool_calls[call_idx]
                    screenshot_str = call.get("result", {}).get("screenshot")
                    if screenshot_str:
                        hash_val, img_idx = extract_screenshot_hash(screenshot_str)
                        if hash_val and img_idx is not None:
                            screenshot_map[call_idx] = img_idx
                
                # Collect tool calls only in the range between user messages
                for call_idx in range(start_idx or 0, end_idx):
                    call = tool_calls[call_idx]
                    if not (call["name"] == "message" and call.get("role", "user") == "user"):
                        desc = call["name"]
                        screenshot_idx = screenshot_map.get(call_idx)
                        
                        # Add details for computer calls
                        if call["name"] == "computer":
                            try:
                                args = json.loads(call.get("arguments", "{}"))
                                action = args.get("action")
                                x = args.get("x")
                                y = args.get("y")
                                if action and x is not None and y is not None:
                                    desc = f"computer: {action} at ({x}, {y})"
                                elif action:
                                    desc = f"computer: {action}"
                            except Exception:
                                pass
                        
                        # Create tool call entry with optional screenshot
                        tool_call_entry = {"name": desc}
                        if screenshot_idx is not None and screenshot_idx < len(screenshots):
                            # Save individual screenshot for this tool call
                            screenshot_name = f"screenshot_{gif_idx}_{call_idx}.png"
                            screenshot_path = gif_dir / screenshot_name
                            screenshots[screenshot_idx].save(screenshot_path, format="PNG")
                            tool_call_entry["screenshot"] = str(screenshot_path.relative_to(gif_dir.parent.parent))
                        
                        tool_calls_list.append(tool_call_entry)
                output.append({
                    "prompt": prompt,
                    "gif": str(gif_path.relative_to(gif_dir.parent.parent)) if gif_path else None,
                    "tool_calls": tool_calls_list
                })
            else:
                i += 1

    # Save output array
    output_json = output_json or (gif_dir.parent / "trajectory_nodes.json")
    with open(output_json, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote {len(output)} nodes to {output_json}")
    return output

def main():
    parser = argparse.ArgumentParser(description="Convert a HuggingFace dataset to trajectory nodes with GIFs")
    parser.add_argument("dataset_path", help="Path to HuggingFace dataset")
    parser.add_argument("-o", "--output", help="Output JSON path")
    parser.add_argument("--gif_dir", help="Directory to save GIFs")
    args = parser.parse_args()
    process_dataset(args.dataset_path, args.output, args.gif_dir)

if __name__ == "__main__":
    main()
