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
    prompt = """Andy Warhol style pop art crypto laundromat, 3x3 grid composition showing retro washing machines but instead of clothes, 
    they're cleaning dirty fiat bills and outputting clean Bitcoin, Ethereum, and crypto tokens, 
    each panel in different vibrant pop colors (electric blue, hot pink, neon green, bright red, purple, yellow, orange, cyan, magenta), 
    high contrast screenprint aesthetic, clean lines, 1960s commercial art style, 
    washing machine displays showing blockchain confirmations instead of wash cycles, 
    soap bubbles replaced with floating crypto symbols (₿, Ξ, ◆), 
    people in business suits feeding dirty cash into machines while clean digital coins pour out, 
    "CRYPTO WASH" neon signs, coin-operated but with hardware wallets instead of quarters, 
    retro-futuristic laundromat aesthetic meets cryptocurrency revolution, 
    commentary on financial system transformation and money laundering jokes, 
    bold saturated colors, repetitive Warhol-style imagery, commercial pop art aesthetic"""
    
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
                    "caption": "🏪💸 THE CRYPTO LAUNDROMAT 💸🏪\n\nInsert dirty fiat 💵 → Get clean Bitcoin ₿\n\nWarhol meets DeFi in this pop art masterpiece! Watch traditional money get the blockchain treatment in our retro-futuristic washing machines. Each cycle = 6 confirmations! 🔄\n\n#PixelWarhol #CryptoArt #PopArt #Bitcoin #DeFi #WarholStyle #CryptoMemes #DigitalArt #NFT #BlockchainArt",
                    "hashtags": ["#PixelWarhol", "#CryptoArt", "#PopArt", "#Bitcoin", "#DeFi", "#WarholStyle", "#CryptoMemes", "#DigitalArt", "#NFT", "#BlockchainArt"]
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