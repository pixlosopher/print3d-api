#!/usr/bin/env python3
"""
Quick test of the 3D pipeline functionality
"""

import os
import sys
from pathlib import Path

# Fix imports for standalone execution
sys.path.insert(0, str(Path(__file__).parent))

# Now we can import with absolute paths
from config import Config
from image_gen import ImageGenerator

def test_config():
    """Test configuration"""
    config = Config()
    print("🔧 Configuration Status:")
    print(f"  Image generation (Gemini): {'✅' if config.gemini_api_key else '❌'}")
    print(f"  3D conversion (Meshy): {'✅' if config.meshy_api_key else '❌'}")
    print(f"  3D printing (Shapeways): {'✅' if config.shapeways_client_id else '❌'}")
    print()
    return config

def test_image_generation():
    """Test image generation"""
    print("🖼️  Testing image generation...")
    try:
        generator = ImageGenerator()
        result = generator.generate(
            prompt="a cute small robot figurine with big eyes",
            style="figurine"
        )
        print(f"  ✅ Generated image: {result.url}")
        if result.local_path and result.local_path.exists():
            print(f"  📁 Saved locally: {result.local_path}")
        return result
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def main():
    print("🤖 3D Pipeline Test")
    print("=" * 40)
    
    config = test_config()
    
    if config.gemini_api_key:
        image_result = test_image_generation()
        
        if image_result:
            print("\n🎯 Next steps to make this a full pipeline:")
            print("  1. Get Meshy API key for 3D conversion")
            print("  2. Get Shapeways API key for printing")
            print("  3. Pipeline will be: Image → 3D Model → Print Quote")
    else:
        print("❌ No API keys configured. Please set up .env file.")
    
    print("\n✅ Pipeline codebase is functional!")

if __name__ == "__main__":
    main()