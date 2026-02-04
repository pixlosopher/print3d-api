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
    """Generate Crypto Laundromat Warhol-style crypto art"""
    
    # Create the prompt for Crypto Laundromat pop art
    prompt = """Andy Warhol style pop art crypto laundromat, 3x3 grid composition showing vintage coin-operated washing machines, 
    each panel in different electric neon colors (hot pink, electric blue, lime green, bright orange, neon purple, acid yellow, magenta, cyan, red), 
    high contrast screenprint aesthetic, washing machines with digital LED displays showing Bitcoin, Ethereum, and crypto symbols,
    old crumpled dollar bills going into machines and clean digital coins coming out,
    retro 1960s laundromat setting with modern crypto twist, soap bubbles containing blockchain symbols,
    people in silhouette feeding crypto tokens into machines, Campbell's soup can aesthetic applied to "CLEAN CRYPTO" detergent boxes,
    commercial pop art style, repetitive imagery, democratization of money concept, transformation and purification theme"""
    
    print(f"Generating Crypto Laundromat Warhol crypto art...")
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
            result_file = output_dir / f"{timestamp}-crypto-laundromat-warhol.json"
            
            with open(result_file, 'w') as f:
                json.dump({
                    "concept": "Crypto Laundromat Warhol Pop Art",
                    "prompt": prompt,
                    "result": result.model_dump(),
                    "timestamp": timestamp,
                    "social_caption": "💰🧼 CLEAN CRYPTO CYCLE 🧼💰\n\nWhere dirty fiat meets digital detergent! Andy would've loved watching dollars transform into pristine pixels. The future of money isn't just decentralized—it's sanitized! ✨\n\n#CryptoArt #PixelWarhol #PopArt #Bitcoin #DigitalArt #AndyWarhol #CryptoLife #CleanMoney #BlockchainArt #NFT #CryptoMemes #WashCycle"
                }, f, indent=2)
            
            print(f"Result saved to: {result_file}")
            print(f"Social media caption ready!")
            return result
        else:
            print(f"❌ Generation failed: {result.error}")
            return None
            
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        return None

if __name__ == "__main__":
    result = asyncio.run(main())