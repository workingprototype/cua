#!/usr/bin/env python3
"""
ScreenSpot-Pro Benchmark Script

Evaluates models on the ScreenSpot-Pro dataset for click prediction accuracy.
Supports both ComputerAgent model strings and custom model classes.
"""

import asyncio
from typing import Optional

from datasets import load_dataset
from tqdm import tqdm

from utils import (
    ModelWrapper, 
    is_click_in_bbox, 
    save_results_to_markdown, 
    save_visualizations,
    get_available_models
)


async def evaluate_model(model_wrapper: ModelWrapper, dataset, max_samples: Optional[int] = None) -> dict:
    """
    Evaluate a model on the ScreenSpot-Pro dataset.
    
    Args:
        model_wrapper: ModelWrapper instance
        dataset: ScreenSpot-Pro dataset (list of samples)
        max_samples: Maximum number of samples to evaluate (None for all)
        
    Returns:
        Dictionary with evaluation results
    """
    print(f"\nEvaluating model: {model_wrapper.model_name}")
    
    # Load model
    await model_wrapper.load_model()
    
    total_samples = len(dataset)
    if max_samples is not None:
        total_samples = min(max_samples, total_samples)
    
    correct_predictions = 0
    failed_predictions = 0
    results = []
    
    try:
        for i in tqdm(range(total_samples), desc=f"Evaluating {model_wrapper.model_name}"):
            sample = dataset[i]
            
            # Extract sample data
            image = sample['image']
            instruction = sample['instruction']
            bbox = sample['bbox']  # [x1, y1, x2, y2]
            sample_id = sample['id']
            
            # Predict click coordinates
            try:
                click_coords = await model_wrapper.predict_click(image, instruction)
                
                # Check if prediction is correct
                is_correct = is_click_in_bbox(click_coords, bbox)
                
                if is_correct:
                    correct_predictions += 1
                
                results.append({
                    'id': sample_id,
                    'instruction': instruction,
                    'bbox': bbox,
                    'predicted_coords': click_coords,
                    'is_correct': is_correct,
                    'failed': False
                })
                
            except Exception as e:
                print(f"\nError predicting sample {sample_id}: {e}")
                failed_predictions += 1
                results.append({
                    'id': sample_id,
                    'instruction': instruction,
                    'bbox': bbox,
                    'predicted_coords': None,
                    'is_correct': False,
                    'failed': True,
                    'error': str(e)
                })
    
    finally:
        # Unload model
        await model_wrapper.unload_model()
    
    # Calculate metrics
    accuracy = correct_predictions / total_samples if total_samples > 0 else 0.0
    failure_rate = failed_predictions / total_samples if total_samples > 0 else 0.0
    
    return {
        'model_name': model_wrapper.model_name,
        'total_samples': total_samples,
        'correct_predictions': correct_predictions,
        'failed_predictions': failed_predictions,
        'accuracy': accuracy,
        'failure_rate': failure_rate,
        'results': results
    }


async def main():
    """
    Main function to run the benchmark.
    """
    # Load dataset
    print("Loading ScreenSpot-Pro dataset...")
    ds = load_dataset("lmms-lab/ScreenSpot-Pro")
    dataset = ds['train'] # type: ignore
    # Convert to list to support indexing
    dataset_list = list(dataset)
    print(f"Dataset loaded: {len(dataset_list)} samples")
    
    # Get available models
    models = get_available_models()
    
    # Evaluation settings
    max_samples = 5  # Set to None to evaluate on full dataset
    
    # Run evaluations
    all_results = []
    
    for model in models:
        try:
            model_wrapper = ModelWrapper(model)
            result = await evaluate_model(model_wrapper, dataset_list, max_samples)
            all_results.append(result)
            
            # Print summary
            print(f"\n{result['model_name']} Results:")
            print(f"  Accuracy: {result['accuracy']*100:.2f}%")
            print(f"  Correct: {result['correct_predictions']}/{result['total_samples']}")
            print(f"  Failed: {result['failed_predictions']}")
            
        except Exception as e:
            print(f"\nError evaluating model {model}: {e}")
            continue
    
    # Save results
    if all_results:
        save_results_to_markdown(all_results)
        save_visualizations(all_results, dataset_list)
        print("\nBenchmark completed successfully!")
    else:
        print("\nNo successful evaluations completed.")


if __name__ == "__main__":
    asyncio.run(main())