#!/usr/bin/env python3
"""
Shared utilities for ScreenSpot-Pro benchmarking and interactive testing.
"""

import asyncio
import base64
import os
import sys
from datetime import datetime
from io import BytesIO
from typing import List, Union, Tuple, Optional

from PIL import Image, ImageDraw
from tqdm import tqdm
import gc
import torch

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from agent.agent import ComputerAgent
from models import GTA1Model
from models.base import ModelProtocol

def get_available_models() -> List[Union[str, ModelProtocol]]:
    """
    Get list of available models for testing.
    
    Returns:
        List of model strings and model classes
    """
    local_provider = "huggingface-local/"  # Options: huggingface-local/ or mlx/
    
    models = [
        # === ComputerAgent model strings ===
        f"{local_provider}HelloKKMe/GTA1-7B",
        # f"{local_provider}HelloKKMe/GTA1-32B",  # Uncomment if you have this model
        
        # === Reference model classes ===
        GTA1Model("HelloKKMe/GTA1-7B"),
        # GTA1Model("HelloKKMe/GTA1-32B"),  # Uncomment if you have this model
    ]
    
    return models


def is_click_in_bbox(click_coords: Optional[Tuple[int, int]], bbox: List[int]) -> bool:
    """
    Check if click coordinates are within the bounding box.
    
    Args:
        click_coords: (x, y) coordinates or None
        bbox: [x1, y1, x2, y2] bounding box
        
    Returns:
        True if click is within bbox, False otherwise
    """
    if click_coords is None:
        return False
    
    x, y = click_coords
    x1, y1, x2, y2 = bbox
    
    return x1 <= x <= x2 and y1 <= y <= y2


def image_to_base64(image: Image.Image) -> str:
    """
    Convert PIL Image to base64 string.
    
    Args:
        image: PIL Image
        
    Returns:
        Base64 encoded image string
    """
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


class ModelWrapper:
    """
    Wrapper to provide unified interface for both ComputerAgent and custom models.
    """
    
    def __init__(self, model: Union[str, ModelProtocol]):
        self.model = model
        self.is_computer_agent = isinstance(model, str)
        self.agent: Optional[ComputerAgent] = None
        
        if self.is_computer_agent:
            self.model_name = str(model)
        else:
            self.model_name = f"models.{model.__class__.__name__}"
    
    async def load_model(self) -> None:
        """Load the model."""
        if self.is_computer_agent:
            self.agent = ComputerAgent(model=str(self.model))
        else:
            await self.model.load_model() # type: ignore
    
    async def unload_model(self) -> None:
        """Unload the model."""
        if not self.is_computer_agent:
            await self.model.unload_model() # type: ignore
        else:
            del self.agent
            self.agent = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    
    async def predict_click(self, image: Image.Image, instruction: str) -> Optional[Tuple[int, int]]:
        """Predict click coordinates."""
        if self.is_computer_agent:
            if self.agent is None:
                await self.load_model()
            
            if self.agent is not None:
                image_b64 = image_to_base64(image)
                result = await self.agent.predict_click(instruction=instruction, image_b64=image_b64)
                return result
            return None
        else:
            return await self.model.predict_click(image, instruction) # type: ignore


def save_results_to_markdown(all_results: List[dict], output_file: str = "screenspot_pro_results.md") -> None:
    """
    Save evaluation results to a markdown table.
    
    Args:
        all_results: List of evaluation results for each model
        output_file: Output markdown file path
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# ScreenSpot-Pro Benchmark Results\n\n")
        f.write(f"**Evaluation Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Summary table
        f.write("## Summary\n\n")
        f.write("| Model | Total Samples | Correct | Failed | Accuracy | Failure Rate |\n")
        f.write("|-------|---------------|---------|--------|----------|--------------|\n")
        
        for result in all_results:
            model_name = result['model_name']
            total = result['total_samples']
            correct = result['correct_predictions']
            failed = result['failed_predictions']
            accuracy = result['accuracy'] * 100
            failure_rate = result['failure_rate'] * 100
            
            f.write(f"| {model_name} | {total} | {correct} | {failed} | {accuracy:.2f}% | {failure_rate:.2f}% |\n")
        
        # Detailed results for each model
        for result in all_results:
            f.write(f"\n## {result['model_name']} - Detailed Results\n\n")
            f.write("| Sample ID | Instruction | BBox | Predicted | Correct | Failed |\n")
            f.write("|-----------|-------------|------|-----------|---------|--------|\n")
            
            for sample_result in result['results'][:10]:  # Show first 10 samples
                sample_id = sample_result['id']
                instruction = sample_result['instruction'][:50] + "..." if len(sample_result['instruction']) > 50 else sample_result['instruction']
                bbox = str(sample_result['bbox'])
                predicted = str(sample_result['predicted_coords']) if sample_result['predicted_coords'] else "None"
                correct = "PASS" if sample_result['is_correct'] else "FAIL"
                failed = "YES" if sample_result['failed'] else "NO"
                
                f.write(f"| {sample_id} | {instruction} | {bbox} | {predicted} | {correct} | {failed} |\n")
            
            if len(result['results']) > 10:
                f.write(f"\n*Showing first 10 of {len(result['results'])} samples*\n")
    
    print(f"\nResults saved to: {output_file}")


def save_visualizations(all_results: List[dict], dataset_list, output_dir: str = "output") -> None:
    """
    Save visualizations of predicted coordinates vs bboxes to an output folder.
    
    Args:
        all_results: List of evaluation results for each model
        dataset_list: List of dataset samples
        output_dir: Output directory path
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    for result in all_results:
        model_name = result['model_name'].replace('/', '_').replace('.', '_')
        model_dir = os.path.join(output_dir, model_name)
        os.makedirs(model_dir, exist_ok=True)
        
        print(f"\nSaving visualizations for {result['model_name']}...")
        
        for i, sample_result in enumerate(tqdm(result['results'][:10], desc=f"Saving {model_name} visualizations")):
            try:
                # Find the original sample
                sample_id = sample_result['id']
                sample = None
                for s in dataset_list:
                    if s['id'] == sample_id:
                        sample = s
                        break
                
                if sample is None:
                    continue
                
                # Get image and data
                image = sample['image'].copy()
                bbox = sample_result['bbox']  # [x1, y1, x2, y2]
                predicted_coords = sample_result['predicted_coords']
                is_correct = sample_result['is_correct']
                
                # Draw on image
                draw = ImageDraw.Draw(image)
                
                # Draw bounding box (ground truth) in green
                x1, y1, x2, y2 = bbox
                draw.rectangle([x1, y1, x2, y2], outline="green", width=3)
                draw.text((x1, y1-20), "Ground Truth", fill="green")
                
                # Draw predicted click in red or blue
                if predicted_coords is not None:
                    px, py = predicted_coords
                    color = "blue" if is_correct else "red"
                    # Draw crosshair
                    crosshair_size = 15
                    draw.line([(px-crosshair_size, py), (px+crosshair_size, py)], fill=color, width=3)
                    draw.line([(px, py-crosshair_size), (px, py+crosshair_size)], fill=color, width=3)
                    draw.text((px+10, py-20), f"Predicted ({px},{py})", fill=color)
                
                # Add status text
                status = "CORRECT" if is_correct else "INCORRECT"
                status_color = "blue" if is_correct else "red"
                draw.text((10, 10), f"Status: {status}", fill=status_color)
                draw.text((10, 30), f"Instruction: {sample_result['instruction'][:50]}...", fill="black")
                
                # Save image
                filename = f"sample_{i+1:02d}_{sample_id}_{status.lower()}.png"
                filepath = os.path.join(model_dir, filename)
                image.save(filepath)
                
            except Exception as e:
                print(f"Error saving visualization for sample {sample_id}: {e}")
                continue
        
        print(f"Visualizations saved to: {model_dir}")


def save_prediction_visualization(image: Image.Image, instruction: str, predictions: List[dict], 
                                output_file: str = "interactive_prediction.png") -> None:
    """
    Save visualization of multiple model predictions on a single image.
    
    Args:
        image: PIL Image to visualize
        instruction: Instruction text
        predictions: List of prediction dicts with keys: model_name, coords, error
        output_file: Output file path
    """
    # Create a copy of the image
    vis_image = image.copy()
    draw = ImageDraw.Draw(vis_image)
    
    # Colors for different models
    colors = ["red", "blue", "orange", "purple", "brown", "pink", "gray", "olive"]
    
    # Draw predictions
    for i, pred in enumerate(predictions):
        color = colors[i % len(colors)]
        model_name = pred['model_name']
        coords = pred.get('coords')
        error = pred.get('error')
        
        if coords is not None:
            px, py = coords
            # Draw crosshair
            crosshair_size = 20
            draw.line([(px-crosshair_size, py), (px+crosshair_size, py)], fill=color, width=4)
            draw.line([(px, py-crosshair_size), (px, py+crosshair_size)], fill=color, width=4)
            # Draw model name
            draw.text((px+15, py+15), f"{model_name}: ({px},{py})", fill=color)
        else:
            # Draw error text
            draw.text((10, 50 + i*20), f"{model_name}: ERROR - {error}", fill=color)
    
    # Add instruction at the top
    draw.text((10, 10), f"Instruction: {instruction}", fill="black")
    
    # Save image
    vis_image.save(output_file)
    print(f"Prediction visualization saved to: {output_file}")


def take_screenshot() -> Image.Image:
    """
    Take a screenshot of the current screen.
    
    Returns:
        PIL Image of the screenshot
    """
    try:
        import pyautogui
        screenshot = pyautogui.screenshot()
        return screenshot
    except ImportError:
        print("pyautogui not installed. Please install it with: pip install pyautogui")
        raise
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        raise

