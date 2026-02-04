#!/usr/bin/env python3
"""
Basic example of using the print3d pipeline.

Run with:
    python examples/basic_pipeline.py "a cute robot"
"""

import sys
from pathlib import Path

# Add parent to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent))

from print3d import Pipeline, ImageStyle
from print3d.pipeline import PipelineStage


def main():
    # Get prompt from command line or use default
    prompt = sys.argv[1] if len(sys.argv) > 1 else "a cute robot with big eyes"
    
    print(f"🚀 Starting pipeline for: '{prompt}'\n")
    
    # Check configuration
    pipeline = Pipeline.from_env(output_dir="./output")
    config_status = pipeline.check_config()
    
    print("📋 Configuration:")
    print(f"   Image Gen: {'✅' if config_status['image_generation'] else '❌'}")
    print(f"   Mesh Gen:  {'✅' if config_status['mesh_conversion'] else '❌'}")
    print(f"   Printing:  {'✅' if config_status['print_service'] else '❌'}")
    
    if config_status['missing']:
        print(f"\n⚠️  Missing: {', '.join(config_status['missing'])}")
        print("   Set up API keys in .env file")
        return
    
    print()
    
    # Progress callback
    def on_progress(stage: PipelineStage, progress: float, message: str):
        bar = "█" * int(progress * 20) + "░" * (20 - int(progress * 20))
        print(f"\r   [{bar}] {message:<50}", end="", flush=True)
    
    # Run pipeline
    try:
        result = pipeline.run(
            prompt=prompt,
            style=ImageStyle.FIGURINE,
            size_mm=50,
            skip_print_upload=not config_status['print_service'],
            on_progress=on_progress,
        )
        
        print("\n")
        
        if result.is_complete:
            print("✅ Pipeline complete!\n")
            print(f"   📸 Image: {result.image_path}")
            print(f"   🎨 Mesh:  {result.mesh_path}")
            print(f"   ⏱️  Time:  {result.duration_seconds:.1f}s")
            
            if result.validation:
                status = "✅ Valid" if result.validation.is_valid else "⚠️  Has issues"
                print(f"   🔍 Mesh:  {status}")
            
            if result.pricing:
                print(f"\n💰 Pricing ({len(result.pricing.materials)} materials):")
                for m in result.pricing.materials[:5]:
                    print(f"      {m.name}: ${m.price:.2f}")
                
                if result.pricing.cheapest:
                    print(f"\n   Cheapest: ${result.pricing.cheapest.price:.2f} ({result.pricing.cheapest.name})")
            
            # Save result
            result_path = Path("./output/result.json")
            result.save(result_path)
            print(f"\n   📄 Saved: {result_path}")
            
        else:
            print(f"❌ Pipeline failed: {result.error}")
            
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
