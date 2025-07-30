# Computer Agent Benchmarks

This directory contains benchmarks designed to test agent providers in the Computer Agent SDK against reference agent implementations.

## Overview

The benchmark system evaluates models on GUI grounding tasks, specifically click prediction accuracy. It supports both:
- **Computer Agent SDK providers** (using model strings like `"huggingface-local/HelloKKMe/GTA1-7B"`)
- **Reference agent implementations** (custom model classes implementing the `ModelProtocol`)

## Available Benchmarks

### 1. ScreenSpot-v2 (`ss-v2.py`)
- **Dataset**: ScreenSpot-v2 (click-only GUI grounding)
- **Format**: Standard resolution screenshots
- **Task**: Predict click coordinates given an instruction and image
- **Metrics**: Accuracy, Error Rate, Timing, VRAM usage

### 2. ScreenSpot-Pro (`ss-pro.py`) 
- **Dataset**: ScreenSpot-Pro (high-resolution click-only GUI grounding)
- **Format**: High-resolution screenshots
- **Task**: Predict click coordinates given an instruction and image
- **Metrics**: Accuracy, Error Rate, Timing, VRAM usage

### 3. Interactive Testing (`interactive.py`)
- **Real-time testing**: Take screenshots and visualize model predictions
- **Commands**: 
  - Type instruction → screenshot + test all models
  - `screenshot` → take screenshot without prediction
  - `models` → list available models
  - `quit`/`exit` → exit tool
- **Output**: Visual predictions with crosshairs for each model

## Adding Reference Agent Implementations

### 1. Implement the ModelProtocol

Create a new file in `models/` directory implementing the `ModelProtocol`:

```python
from models.base import ModelProtocol
from typing import Optional, Tuple
from PIL import Image

class YourModelName(ModelProtocol):
    def __init__(self, model_path: str):
        self.model_path = model_path
        self._model = None
    
    @property
    def model_name(self) -> str:
        return self.model_path
    
    async def load_model(self) -> None:
        """Load the model into memory."""
        # Your model loading logic here
        pass
    
    async def unload_model(self) -> None:
        """Unload the model from memory."""
        # Your model cleanup logic here
        pass
    
    async def predict_click(self, image: Image.Image, instruction: str) -> Optional[Tuple[int, int]]:
        """
        Predict click coordinates for the given image and instruction.
        
        Args:
            image: PIL Image to analyze
            instruction: Text instruction describing what to click
            
        Returns:
            Tuple of (x, y) coordinates or None if prediction fails
        """
        # Your prediction logic here
        return (x, y)  # Return predicted coordinates
```

### 2. Register Your Model

Add your model to the `get_available_models()` function in `utils.py`:

```python
def get_available_models() -> List[Union[str, ModelProtocol]]:
    models = [
        # Computer Agent SDK providers
        "huggingface-local/HelloKKMe/GTA1-7B",
        
        # Reference implementations
        GTA1Model("HelloKKMe/GTA1-7B"),
        YourModelName("path/to/your/model"),  # Add your model here
    ]
    return models
```

## Running Benchmarks

### 1. Configure Models
Edit `utils.py` to specify which models you want to test in `get_available_models()`.

### 2. Run Benchmark
```bash
# ScreenSpot-v2 benchmark
python ss-v2.py --samples 50

# ScreenSpot-Pro benchmark  
python ss-pro.py --samples 50

# Interactive testing
python interactive.py
```

## Output

### Console Output
```
Model Results:
  Accuracy: 85.50% (171/200)
  Avg Time: 1.23s (0.89s - 2.45s)
  VRAM Usage: 4.5GB (max) / 3.4GB (avg)
```

### Generated Files
- **Markdown Report**: `*_results.md` with detailed results tables
- **Visualizations**: `output/` directory with prediction visualizations
- **Interactive Output**: `interactive_output/` for interactive session results

## Metrics Tracked

- **Accuracy**: Percentage of clicks within bounding boxes
- **Timing**: Average, min, max prediction times
- **VRAM Usage**: Maximum and average GPU memory usage
- **Per-sample Results**: Detailed breakdown for debugging

## Architecture

The benchmark system is designed for:
- **Modularity**: Easy to add new models and benchmarks
- **Flexibility**: Works with any iterator of dicts with `image`, `bbox`, `instruction` keys
- **Performance**: VRAM tracking and timing analysis
- **Visualization**: Automatic generation of prediction visualizations

## Contributing

To add a new benchmark:
1. Create a new script following the pattern in `ss-v2.py`
2. Use the `evaluate_model()` function from utils
3. Ensure your dataset yields dicts with `image`, `bbox`, `instruction` keys
4. Update this README with benchmark details
