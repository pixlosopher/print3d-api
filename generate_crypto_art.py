#!/usr/bin/env python3

import sys
import json
from pathlib import Path
import asyncio
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config
from image_gen import ImageGenerator, ImageStyle

async def main():
    """Generate Bitcoin ATM Warhol-style crypto art"""
    
    # Create the prompt for Bitcoin ATM pop art
    prompt = """Andy Warhol style pop art Bitcoin ATM shrine, 2x2 grid composition showing a Bitcoin ATM machine, 
    each panel in different vibrant colors (electric blue, hot pink, neon yellow, bright red), 
    high contrast screenprint aesthetic, clean lines, retro-futuristic design, Bitcoin symbols and QR codes visible on screen, 
    people silhouettes using the ATM, commercial art style, bold saturated colors, repetitive imagery, 
    1960s pop art aesthetic mixed with cryptocurrency symbols, crypto accessibility and democratization theme"""
    
    print(f"Generating Bitcoin ATM Warhol crypto art...")
    print(f"Prompt: {prompt[:100]}...")
    
    # Initialize the image generator
    generator = ImageGenerator()
    
    # Generate the image
    try:
        result = await generator.generate_async(
            prompt=prompt,
            style=ImageStyle.CUSTOM,
            size="square"
        )
        
        if result.status == "success":
            print(f"\n✅ Image generated successfully!")
            print(f"Image URL: {result.image_url}")
            print(f"Timestamp: {result.timestamp}")
            
            # Save result info
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            result_file = output_dir / f"{timestamp}-bitcoin-atm-warhol.json"
            
            with open(result_file, 'w') as f:
                json.dump({
                    "concept": "Bitcoin ATM Warhol Pop Art",
                    "prompt": prompt,
                    "result": result.model_dump(),
                    "timestamp": timestamp
                }, f, indent=2)
            
            print(f"Result saved to: {result_file}")
            return result
        else:
            print(f"❌ Generation failed: {result.error}")
            return None
            
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        return None

if __name__ == "__main__":
    result = asyncio.run(main())