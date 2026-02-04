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
    """Generate Crypto Diner Warhol-style crypto art"""
    
    # Create the prompt for Crypto Diner pop art - NEW CONCEPT
    prompt = """Andy Warhol style pop art crypto diner, 3x3 grid composition showing retro 1950s American diner,
    each panel in different electric neon colors (hot pink, electric blue, lime green, bright orange, neon purple, acid yellow, magenta, cyan, red),
    high contrast screenprint aesthetic, vintage diner counter with chrome stools and checkered floor,
    neon signs reading "CRYPTO DINER", "SATOSHI'S BURGERS", "HODL HOTDOGS", "BLOCKCHAIN BREAKFAST",
    waitress in 1950s uniform serving plates of Bitcoin symbols, milkshakes with Ethereum logos,
    jukebox playing "MOON MUSIC", pie display case filled with altcoin pies (DOGE, ADA, SOL),
    customers are silhouettes paying with crypto wallets, cash register showing digital prices,
    Campbell's soup can aesthetic applied to "DIGITAL SOUP" cans on shelves,
    nostalgic Americana meets futuristic finance, retro-futurism pop art style,
    repetitive diner imagery, democratization of crypto through familiar American imagery"""
    
    print(f"Generating Crypto Diner Warhol crypto art...")
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
            result_file = output_dir / f"{timestamp}-crypto-diner-warhol.json"
            
            with open(result_file, 'w') as f:
                json.dump({
                    "concept": "Crypto Diner Warhol Pop Art",
                    "prompt": prompt,
                    "result": result.model_dump(),
                    "timestamp": timestamp,
                    "social_caption": "🍔💰 WELCOME TO SATOSHI'S DINER! 💰🍔\n\nWhere American dreams meet digital dollars! Andy would've loved this retro-crypto fusion - classic diner vibes serving up the future of finance. From HODL hotdogs to blockchain breakfast, we're cooking up the revolution! 🚀✨\n\n#CryptoArt #PixelWarhol #PopArt #Bitcoin #DigitalArt #AndyWarhol #CryptoDiner #RetroFuture #BlockchainArt #NFT #CryptoLife #SatoshiStyle"
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