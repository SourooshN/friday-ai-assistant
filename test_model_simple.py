"""
Simple test for ModelManager to debug the context issue
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

async def test_model_manager():
    from core.models.model_manager import ModelManager
    
    print("Testing ModelManager...")
    
    # Minimal config
    config = {
        'host': 'http://localhost:11434',
        'default_model': 'openhermes:latest'
    }
    
    mm = ModelManager(config)
    await mm.initialize()
    
    print(f"Available models: {len(mm.available_models)}")
    
    # Test generation
    try:
        result = await mm.generate(
            prompt="Say 'test passed' and nothing else",
            max_tokens=10
        )
        print(f"✓ Generation successful: {result.text}")
    except Exception as e:
        print(f"✗ Generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_model_manager())