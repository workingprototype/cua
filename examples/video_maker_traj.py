"""
Video Maker for Trajectory Dataset

This script processes a trajectory dataset folder, extracts frames,
and creates an animated video with cursor overlays.
"""

from utils import load_dotenv_files
load_dotenv_files()

import os
import json
import math
import shutil
import re
from pathlib import Path
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import requests
from io import BytesIO
from tqdm import tqdm

# Constants
CURSOR_SCALE = 2  # Scale factor for cursor size
FRAMES_PER_CLICK = 8  # Number of frames to show for click animation
FRAMES_PER_MOVE = 10  # Number of frames to interpolate between cursor positions
CURSOR_NORMAL = "https://mac-cursors.netlify.app/png/default@2x.png"
CURSOR_CLICKING = "https://mac-cursors.netlify.app/png/handpointing@2x.png"
CURSOR_TYPING = "https://mac-cursors.netlify.app/png/textcursor@2x.png"
CURSOR_HOTSPOT = (20, 15)
OUTPUT_DIR = "examples/output/video_frames"

# Vignette effect constants
VIGNETTE_WIDTH = 10  # Width of the vignette border in pixels
VIGNETTE_COLORS = [(128, 0, 255), (0, 0, 255)]  # Purple to Blue gradient colors
VIGNETTE_ANIMATION_SPEED = 0.1  # Controls speed of the animation pulse

def download_image(url):
    """Download an image from a URL."""
    response = requests.get(url)
    return Image.open(BytesIO(response.content))

def load_cursor_images():
    """Load and resize cursor images."""
    cursor_normal = download_image(CURSOR_NORMAL)
    cursor_clicking = download_image(CURSOR_CLICKING)
    cursor_typing = download_image(CURSOR_TYPING)
    
    # Resize all cursors based on CURSOR_SCALE
    width_normal, height_normal = cursor_normal.size
    width_clicking, height_clicking = cursor_clicking.size
    width_typing, height_typing = cursor_typing.size
    
    cursor_normal = cursor_normal.resize((int(width_normal * CURSOR_SCALE), int(height_normal * CURSOR_SCALE)))
    cursor_clicking = cursor_clicking.resize((int(width_clicking * CURSOR_SCALE), int(height_clicking * CURSOR_SCALE)))
    cursor_typing = cursor_typing.resize((int(width_typing * CURSOR_SCALE), int(height_typing * CURSOR_SCALE)))
    
    cursors = {
        "normal": cursor_normal,
        "clicking": cursor_clicking,
        "typing": cursor_typing
    }
    
    return cursors

# Store the last known cursor position and thought across all frames
last_known_cursor_position = None
last_known_thought = None

def extract_thought_from_api_response(filename):
    """Extract thought from API response for the current frame."""
    global last_known_thought
    
    turn_dir = os.path.dirname(filename)
    api_response_files = [f for f in os.listdir(turn_dir) if f.endswith('_response.json')]
    
    for api_file in api_response_files:
        try:
            with open(os.path.join(turn_dir, api_file), 'r') as f:
                data = json.load(f)
                # Extract content from response
                content = data.get('response', {}).get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Extract the Thought section
                thought_match = re.search(r"Thought: (.*?)(?:\nAction:|$)", content, re.DOTALL)
                if thought_match:
                    thought = thought_match.group(1).strip()
                    if thought:
                        last_known_thought = thought
                        return thought
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            pass
    
    # Return the last known thought if no new thought is found
    return last_known_thought

def extract_cursor_position_from_filename(filename):
    """Extract cursor position from a filename containing click info."""
    global last_known_cursor_position
    
    # For 'screenshot_NNN_click_TIMESTAMP.png', try to extract coordinates
    match = re.search(r'click_(\d+)_(\d+)_\d+\.png$', filename)
    if match:
        position = (int(match.group(1)), int(match.group(2)))
        last_known_cursor_position = position
        return position
    
    # Check if we have position info from API response
    turn_dir = os.path.dirname(filename)
    api_response_files = [f for f in os.listdir(turn_dir) if f.endswith('_response.json')]
    
    for api_file in api_response_files:
        try:
            with open(os.path.join(turn_dir, api_file), 'r') as f:
                data = json.load(f)
                # Extract action from response
                content = data.get('response', {}).get('choices', [{}])[0].get('message', {}).get('content', '')
                # Look for coordinates in the action
                # First try the pattern from the example: click(start_box='(28,15)')
                coord_match = re.search(r"click\(start_box='\((\d+),(\d+)\)'\)", content)
                if coord_match:
                    position = (int(coord_match.group(1)), int(coord_match.group(2)))
                    last_known_cursor_position = position
                    return position
                
                # Try alternative pattern: click(start_box='<|box_start|>(x,y)<|box_end|>')
                alt_match = re.search(r"click\(start_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>'\)", content)
                if alt_match:
                    position = (int(alt_match.group(1)), int(alt_match.group(2)))
                    last_known_cursor_position = position
                    return position
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            pass
    
    # No new position found, return the last known position
    return last_known_cursor_position

def extract_action_from_filename(filename):
    """Determine the action type from the filename pattern."""
    if 'click' in filename:
        return "clicking"
    elif 'type' in filename:
        return "typing"
    else:
        return "normal"

def create_animated_vignette(image, frame_index):
    """
    Create an animated purple/blue gradient vignette effect around the border of the image.
    The animation pulses the colors and gently varies their intensity over time.
    
    Args:
        image: The base image to apply the vignette to
        frame_index: Current frame index for animation timing
    
    Returns:
        Image with vignette effect applied
    """
    # Create a copy of the image to work with
    result = image.copy()
    width, height = result.size
    
    # Create a blank RGBA image for the vignette overlay
    vignette = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vignette)
    
    # Calculate animation phase based on frame index
    phase = math.sin(frame_index * VIGNETTE_ANIMATION_SPEED) * 0.5 + 0.5  # Oscillates between 0 and 1
    
    # Interpolate between the vignette colors based on the animation phase
    color1 = VIGNETTE_COLORS[0]
    color2 = VIGNETTE_COLORS[1]
    animated_color = (
        int(color1[0] + (color2[0] - color1[0]) * phase),
        int(color1[1] + (color2[1] - color1[1]) * phase),
        int(color1[2] + (color2[2] - color1[2]) * phase),
    )
    
    # Draw gradient borders around each edge
    # Top border
    for i in range(VIGNETTE_WIDTH):
        alpha = int(150 * (1 - i / VIGNETTE_WIDTH))
        border_color = animated_color[:3] + (alpha,)
        draw.line([(0, i), (width, i)], fill=border_color, width=1)
        draw.line([(0, height-i-1), (width, height-i-1)], fill=border_color, width=1)
        draw.line([(i, 0), (i, height)], fill=border_color, width=1)
        draw.line([(width-i-1, 0), (width-i-1, height)], fill=border_color, width=1)
    
    # Apply slight blur to smooth the gradient
    vignette = vignette.filter(ImageFilter.GaussianBlur(16))
    
    # Composite the vignette over the original image
    result = Image.alpha_composite(result.convert('RGBA'), vignette)
    
    return result.convert('RGB')  # Convert back to RGB for consistency

def scale_cursor_with_animation(cursor, frame, max_frames, cursor_type):
    """Create springy scale animation for cursor."""
    if cursor_type == "normal":
        return cursor
    
    # For clicking or typing cursors, create a spring effect
    progress = frame / max_frames
    
    # Spring effect calculation - starts big, gets smaller, then back to normal
    if progress < 0.3:
        # Start with larger scale, shrink down
        scale = 1.3 - progress
    elif progress < 0.7:
        # Then bounce back up a bit
        scale = 0.7 + (progress - 0.3) * 0.8
    else:
        # Then settle to normal (1.0)
        scale = 1.0 + (1.0 - progress) * 0.3
    
    # Apply scale
    width, height = cursor.size
    new_width = int(width * scale)
    new_height = int(height * scale)
    return cursor.resize((new_width, new_height))

# Store the last thought bubble position
last_thought_bubble_pos = None

def draw_thought_bubble(image, position, thought_text, frame_index):
    """Draw a thought bubble with the AI's thoughts near the cursor position."""
    global last_thought_bubble_pos
    
    if thought_text is None or position is None:
        return image
        
    # Create a copy of the image to work with
    result = image.copy()
    
    # Set up text parameters
    font_size = 16
    try:
        # Try to use a nice font if available
        from PIL import ImageFont
        try:
            font = ImageFont.truetype("Arial", font_size)
        except IOError:
            # Fallback to default font
            font = ImageFont.load_default()
    except ImportError:
        font = None
    
    # Wrap text to fit in bubble
    max_width = 400  # Max width in pixels
    wrapped_lines = []
    words = thought_text.split()
    current_line = []
    
    for word in words:
        # Add word to current line
        test_line = ' '.join(current_line + [word])
        
        # Create a temporary draw object to measure text width if needed
        temp_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
        
        # Measure the text width
        if font:
            if hasattr(temp_draw, 'textlength'):
                text_width = temp_draw.textlength(test_line, font=font)
            else:
                # Fall back to rough estimation
                text_width = len(test_line) * (font_size * 0.6)
        else:
            # Rough estimation if no font metrics are available
            text_width = len(test_line) * (font_size * 0.6)
        
        if text_width <= max_width:
            current_line.append(word)
        else:
            # Line is full, start a new line
            if current_line:
                wrapped_lines.append(' '.join(current_line))
            current_line = [word]
    
    # Don't forget the last line
    if current_line:
        wrapped_lines.append(' '.join(current_line))
    
    # Limit number of lines for very long thoughts
    max_lines = 8
    if len(wrapped_lines) > max_lines:
        wrapped_lines = wrapped_lines[:max_lines-1] + ["..."]
    
    # Calculate text dimensions
    line_height = font_size + 4
    text_height = len(wrapped_lines) * line_height
    
    # Find the widest line
    if font:
        # Create a draw object to measure text width
        temp_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
        if hasattr(temp_draw, 'textlength'):
            text_width = max(temp_draw.textlength(line, font=font) for line in wrapped_lines)
        else:
            # Fall back to rough estimation
            text_width = max(len(line) * (font_size * 0.6) for line in wrapped_lines)
    else:
        text_width = max(len(line) * (font_size * 0.6) for line in wrapped_lines)
    
    # Add padding
    padding = 20
    bubble_width = text_width + padding * 2
    bubble_height = text_height + padding * 2
    
    # Calculate bubble position - move slowly towards cursor position
    x, y = position
    screen_width, screen_height = image.size
    
    # Default initial position if this is the first bubble
    target_bubble_x = min(x + 30, screen_width - bubble_width - 10)
    target_bubble_y = max(y - bubble_height - 30, 10)
    
    # Ensure target position is fully on screen
    if target_bubble_x < 10:
        target_bubble_x = 10
    if target_bubble_y + bubble_height > screen_height - 10:
        target_bubble_y = screen_height - bubble_height - 10
    
    # Calculate new position with slow movement towards target
    # Very slow movement factor (0.01 means it moves 1% of the distance per frame)
    movement_factor = 0.001
    
    if last_thought_bubble_pos is None:
        # First frame, set to target position
        bubble_x, bubble_y = target_bubble_x, target_bubble_y
    else:
        # Interpolate slowly towards target position
        last_x, last_y = last_thought_bubble_pos
        bubble_x = last_x + (target_bubble_x - last_x) * movement_factor
        bubble_y = last_y + (target_bubble_y - last_y) * movement_factor
    
    # Add a subtle animation effect to the bubble
    # animation_offset = math.sin(frame_index * 0.1) * 2
    # bubble_y += int(animation_offset)
    
    # Store position for next frame
    last_thought_bubble_pos = (bubble_x, bubble_y)
    
    # Draw rounded rectangle for bubble
    corner_radius = 15
    
    # Background with black gaussian blur
    background_color = (0, 0, 0, 180)  # Black with transparency
    outline_color = (50, 50, 50, 255)   # Dark gray outline
    
    # Draw the bubble background - first create an RGBA version
    bubble_img = Image.new('RGBA', result.size, (0, 0, 0, 0))
    bubble_draw = ImageDraw.Draw(bubble_img)
    
    # Draw rounded rectangle
    # Check if rounded_rectangle is available (PIL 8.0.0+)
    if hasattr(bubble_draw, 'rounded_rectangle'):
        bubble_draw.rounded_rectangle(
            [bubble_x, bubble_y, bubble_x + bubble_width, bubble_y + bubble_height],
            radius=corner_radius,
            fill=background_color,
            outline=outline_color,
            width=2
        )
    else:
        # Fall back to regular rectangle if rounded_rectangle not available
        bubble_draw.rectangle(
            [bubble_x, bubble_y, bubble_x + bubble_width, bubble_y + bubble_height],
            fill=background_color,
            outline=outline_color
        )
    
    # Apply gaussian blur to the bubble background
    bubble_img = bubble_img.filter(ImageFilter.GaussianBlur(3))
    
    # Draw small triangle pointing to cursor
    pointer_size = 10
    pointer_x = x + 15
    pointer_y = y - 5
    
    # Make sure pointer is under the bubble
    if pointer_x > bubble_x + bubble_width:
        pointer_x = bubble_x + bubble_width - 20
    elif pointer_x < bubble_x:
        pointer_x = bubble_x + 20
    
    # Create an overlay for the pointer
    pointer_overlay = Image.new('RGBA', result.size, (0, 0, 0, 0))
    pointer_draw = ImageDraw.Draw(pointer_overlay)
    
    # Draw pointer triangle
    # pointer_draw.polygon(
    #     [
    #         (pointer_x, pointer_y),
    #         (pointer_x - pointer_size, pointer_y - pointer_size),
    #         (pointer_x + pointer_size, pointer_y - pointer_size)
    #     ],
    #     fill=background_color,
    #     outline=outline_color
    # )
    
    # Apply gaussian blur to the pointer
    pointer_overlay = pointer_overlay.filter(ImageFilter.GaussianBlur(3))
    
    # Composite the bubble and pointer onto the original image
    result = Image.alpha_composite(result.convert('RGBA'), bubble_img)
    result = Image.alpha_composite(result, pointer_overlay)
    
    # Now draw the text
    draw = ImageDraw.Draw(result)
    text_x = bubble_x + padding
    text_y = bubble_y + padding
    
    text_color = (255, 255, 255, 255)  # White text
    for line in wrapped_lines:
        draw.text((text_x, text_y), line, font=font, fill=text_color)
        text_y += line_height
    
    return result.convert('RGB')

def create_cursor_overlay(base_image, position, cursor_images, thought_text=None, cursor_type="normal", animation_frame=0, frame_index=0):
    """Create an image with cursor overlaid on the base image and thought bubble if available."""
    # Create a copy of the base image
    result = base_image.copy()
    
    # If position is None, return the image without a cursor
    if position is None:
        return result
    
    # Get the appropriate cursor image
    cursor = cursor_images[cursor_type]
    
    # Apply animation scaling if needed
    if cursor_type in ["clicking", "typing"]:
        cursor = scale_cursor_with_animation(cursor, animation_frame, FRAMES_PER_CLICK, cursor_type)
    
    # Calculate position to center the cursor hotspot
    # Cursor hotspot is at (20,15) of the cursor image
    x, y = position
    hotspot_x, hotspot_y = CURSOR_HOTSPOT
    cursor_x = x - (hotspot_x * CURSOR_SCALE)  # X offset for hotspot
    cursor_y = y - (hotspot_y * CURSOR_SCALE)  # Y offset for hotspot
    
    # Paste the cursor onto the image
    result.paste(cursor, (int(cursor_x), int(cursor_y)), cursor)
    
    # Add thought bubble if text is available
    if thought_text:
        result = draw_thought_bubble(result, position, thought_text, frame_index)
    
    return result

def get_screenshot_files(trajectory_dir):
    """
    Get all screenshot files from a trajectory directory, sorted by sequence number.
    
    Args:
        trajectory_dir: Path to trajectory directory containing turn_XXX folders
        
    Returns:
        List of tuples (path, sequence_number, action_type, position)
    """
    screenshot_files = []
    
    # List all turn directories in order
    turn_dirs = sorted([d for d in os.listdir(trajectory_dir) if d.startswith('turn_')], 
                      key=lambda x: int(x.split('_')[1]))
    
    for turn_dir in turn_dirs:
        turn_path = os.path.join(trajectory_dir, turn_dir)
        if not os.path.isdir(turn_path):
            continue
            
        # Get all screenshot files in this turn
        files = [f for f in os.listdir(turn_path) if f.startswith('screenshot_') and f.endswith('.png')]
        
        for file in files:
            file_path = os.path.join(turn_path, file)
            
            # Extract sequence number from filename (e.g., screenshot_003_...)
            seq_match = re.search(r'screenshot_(\d+)', file)
            if seq_match:
                seq_number = int(seq_match.group(1))
                
                # Determine action type from filename
                action_type = extract_action_from_filename(file)
                
                # Get cursor position if available
                position = extract_cursor_position_from_filename(file_path)
                
                screenshot_files.append((file_path, seq_number, action_type, position))
    
    # Sort by sequence number
    screenshot_files.sort(key=lambda x: x[1])
    
    return screenshot_files

def process_trajectory(trajectory_dir, output_dir, cursors):
    """Process a trajectory directory and create output frames."""
    # Get all screenshot files
    screenshot_files = get_screenshot_files(trajectory_dir)
    
    if not screenshot_files:
        print(f"No screenshot files found in {trajectory_dir}")
        return
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Track frame index
    frame_index = 0
    
    # Process each screenshot
    prev_img = None
    prev_cursor_pos = None
    
    for i, (file_path, seq_number, action_type, position) in enumerate(tqdm(screenshot_files, desc="Processing frames")):
        # Load the current image
        try:
            current_img = Image.open(file_path)
        except Exception as e:
            print(f"Error loading image {file_path}: {e}")
            continue
        
        # Current cursor position
        current_cursor_pos = position
        
        # Check if the current frame has an action (click/typing)
        is_action_frame = action_type in ["clicking", "typing"]
        
        if is_action_frame:
            # If we have a previous frame, use it for the first half of animation
            if prev_img is not None:
                half_frames = FRAMES_PER_CLICK // 2
                # First half of animation uses PREVIOUS image
                for j in range(half_frames):
                    # Get the thought from the API response
                    current_thought = extract_thought_from_api_response(file_path)
                    
                    output_img = create_cursor_overlay(
                        prev_img, current_cursor_pos, cursors,
                        thought_text=current_thought,
                        cursor_type=action_type, 
                        animation_frame=j,
                        frame_index=frame_index
                    )
                    # Apply animated vignette effect
                    output_img = create_animated_vignette(output_img, frame_index)
                    output_img.save(os.path.join(output_dir, f"frame_{frame_index:04d}.png"))
                    frame_index += 1
                
                # Second half uses CURRENT image
                for j in range(half_frames, FRAMES_PER_CLICK):
                    # Get the thought from the API response
                    current_thought = extract_thought_from_api_response(file_path)
                    
                    output_img = create_cursor_overlay(
                        current_img, current_cursor_pos, cursors,
                        thought_text=current_thought,
                        cursor_type=action_type,
                        animation_frame=j,
                        frame_index=frame_index
                    )
                    # Apply animated vignette effect
                    output_img = create_animated_vignette(output_img, frame_index)
                    output_img.save(os.path.join(output_dir, f"frame_{frame_index:04d}.png"))
                    frame_index += 1
            else:
                # If no previous frame, use current for full animation
                for j in range(FRAMES_PER_CLICK):
                    # Get the thought from the API response
                    current_thought = extract_thought_from_api_response(file_path)
                    
                    output_img = create_cursor_overlay(
                        current_img, current_cursor_pos, cursors,
                        thought_text=current_thought,
                        cursor_type=action_type,
                        animation_frame=j,
                        frame_index=frame_index
                    )
                    # Apply animated vignette effect
                    output_img = create_animated_vignette(output_img, frame_index)
                    output_img.save(os.path.join(output_dir, f"frame_{frame_index:04d}.png"))
                    frame_index += 1
        else:
            # Regular frame with normal cursor
            # Get the thought from the API response
            current_thought = extract_thought_from_api_response(file_path)
            
            output_img = create_cursor_overlay(
                current_img, current_cursor_pos, cursors,
                thought_text=current_thought,
                cursor_type="normal",
                frame_index=frame_index
            )
            # Apply animated vignette effect
            output_img = create_animated_vignette(output_img, frame_index)
            output_img.save(os.path.join(output_dir, f"frame_{frame_index:04d}.png"))
            frame_index += 1
        
        # Add position interpolation frames if we're not at the last frame
        if i < len(screenshot_files) - 1:
            # Get next position
            next_cursor_pos = screenshot_files[i+1][3]
            
            # Only interpolate if both positions are valid and different
            if current_cursor_pos is not None and next_cursor_pos is not None and current_cursor_pos != next_cursor_pos:
                for j in range(1, FRAMES_PER_MOVE):
                    progress = j / FRAMES_PER_MOVE
                    interp_x = current_cursor_pos[0] + (next_cursor_pos[0] - current_cursor_pos[0]) * progress
                    interp_y = current_cursor_pos[1] + (next_cursor_pos[1] - current_cursor_pos[1]) * progress
                    interp_pos = (int(interp_x), int(interp_y))
                    
                    # Create interpolated movement frame
                    # Get the thought from the API response
                    current_thought = extract_thought_from_api_response(file_path)
                    
                    output_img = create_cursor_overlay(
                        current_img, interp_pos, cursors,
                        thought_text=current_thought,
                        cursor_type="normal",
                        frame_index=frame_index
                    )
                    # Apply animated vignette effect
                    output_img = create_animated_vignette(output_img, frame_index)
                    output_img.save(os.path.join(output_dir, f"frame_{frame_index:04d}.png"))
                    frame_index += 1
        
        # Save current frame as previous for next iteration
        prev_img = current_img
        prev_cursor_pos = current_cursor_pos

def main():
    """Main function to process the trajectory and create video frames."""
    parser = argparse.ArgumentParser(description='Create a video from a trajectory folder.')
    parser.add_argument('trajectory_dir', type=str, help='Path to the trajectory folder')
    parser.add_argument('--output_dir', type=str, default=OUTPUT_DIR, help='Output directory for video frames')
    parser.add_argument('--fps', type=int, default=24, help='Frames per second for the output video')
    parser.add_argument('--output_video', type=str, default='output_video.mp4', help='Path to output video file')
    parser.add_argument('--skip_ffmpeg', action='store_true', help='Skip running ffmpeg to create video')
    args = parser.parse_args()
    
    trajectory_dir = args.trajectory_dir
    output_dir = args.output_dir
    fps = args.fps
    output_video = args.output_video
    skip_ffmpeg = args.skip_ffmpeg
    
    # Check if trajectory directory exists
    if not os.path.exists(trajectory_dir):
        print(f"Trajectory directory {trajectory_dir} does not exist")
        return
    
    # Clean output directory if it exists
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load cursor images
    print("Loading cursor images...")
    cursors = load_cursor_images()
    
    # Process the trajectory
    print(f"Processing trajectory from {trajectory_dir}...")
    process_trajectory(trajectory_dir, output_dir, cursors)
    
    print(f"Processing complete. Frames saved to {output_dir}")
    
    # Run ffmpeg to create the video
    if not skip_ffmpeg:
        print(f"Running ffmpeg to create video: {output_video}")
        ffmpeg_cmd = f"ffmpeg -y -framerate {fps} -i {output_dir}/frame_%04d.png -c:v libx264 -pix_fmt yuv420p {output_video}"
        try:
            import subprocess
            result = subprocess.run(ffmpeg_cmd, shell=True, check=True, 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                   text=True)
            print(f"Video created successfully: {output_video}")
        except subprocess.CalledProcessError as e:
            print(f"Error running ffmpeg: {e}")
            print(f"ffmpeg output:\n{e.stdout}\n{e.stderr}")
            print("\nYou can create a video manually with this command:")
            print(ffmpeg_cmd)
    else:
        print("Skipping ffmpeg. You can create a video from these frames using ffmpeg with this command:")
        print(f"ffmpeg -framerate {fps} -i {output_dir}/frame_%04d.png -c:v libx264 -pix_fmt yuv420p {output_video}")

if __name__ == "__main__":
    main()
