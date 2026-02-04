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
    """Generate Crypto Vending Machine Warhol-style pop art"""
    
    # Create the prompt for Crypto Vending Machine pop art - fresh concept avoiding all previous themes
    prompt = """Andy Warhol style pop art crypto vending machine, 3x3 grid composition showing a retro vending machine 
    dispensing cryptocurrency tokens and NFTs instead of snacks, each panel in different vibrant pop colors 
    (hot pink, electric blue, lime green, bright orange, purple, yellow, red, cyan, magenta), 
    high contrast screenprint aesthetic, clean bold lines, vintage 1960s vending machine design, 
    crypto coins and NFT cards visible in the dispenser slots, Ethereum logos, Bitcoin symbols, 
    "INSERT WALLET" instead of "INSERT COIN", digital display showing crypto prices, 
    person's silhouette selecting "RARE PEPE" or "DIAMOND HANDS NFT" buttons, 
    commercial pop art style, repetitive imagery, bold saturated colors, 
    retro-futuristic aesthetic, crypto accessibility meets consumer culture theme"""
    
    print(f"Generating Crypto Vending Machine Warhol pop art...")
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
            result_file = output_dir / f"{timestamp}-crypto-vending-warhol.json"
            
            with open(result_file, 'w') as f:
                json.dump({
                    "concept": "Crypto Vending Machine Warhol Pop Art",
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