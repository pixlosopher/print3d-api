#!/usr/bin/env python3
"""
Simple working test using nano-banana-pro directly
"""

import subprocess
from pathlib import Path

def generate_image_for_3d():
    """Generate an image suitable for 3D conversion using nano-banana-pro"""
    
    print("🍌 Generating image with Nano Banana Pro...")
    
    # Use nano-banana-pro skill directly
    skill_path = "/Users/pedrohernandezbaez/Documents/moltbot-2026.1.24/skills/nano-banana-pro"
    output_path = "./output/test-robot.png"
    
    # Make sure output directory exists
    Path("./output").mkdir(exist_ok=True)
    
    # Generate image optimized for 3D printing
    prompt = "a cute small robot figurine with big eyes, simple clean design, solid object, white background, perfect for 3D printing, figurine style, miniature toy"
    
    cmd = [
        "uv", "run", 
        f"{skill_path}/scripts/generate_image.py",
        "--prompt", prompt,
        "--filename", output_path,
        "--resolution", "1K"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        print(f"  Command: {' '.join(cmd[:3])} ...")
        
        if result.returncode == 0:
            print(f"  ✅ Generated: {output_path}")
            print(f"  📁 File exists: {Path(output_path).exists()}")
            if result.stdout:
                print(f"  📄 Output: {result.stdout.strip()}")
            return output_path
        else:
            print(f"  ❌ Error: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return None

def test_3d_pipeline_concept():
    """Show the full pipeline concept"""
    print("\n🚀 3D Pipeline Concept:")
    print("  1. ✅ Image Generation (Nano Banana Pro)")
    print("  2. ⚠️  3D Conversion (Needs Meshy API)")
    print("  3. ⚠️  Print Service (Needs Shapeways API)")
    print("  4. 💰 Cost Estimation")
    print("  5. 📦 Order Management")

def main():
    print("🤖 Real 3D Pipeline Test")
    print("=" * 40)
    
    # Test actual image generation
    image_path = generate_image_for_3d()
    
    test_3d_pipeline_concept()
    
    if image_path:
        print(f"\n✅ Phase 1 working! Next: Get Meshy + Shapeways API keys")
        print(f"📋 To complete pipeline:")
        print(f"   - Add MESHY_API_KEY to .env")
        print(f"   - Add SHAPEWAYS_CLIENT_ID + SHAPEWAYS_CLIENT_SECRET to .env")
        print(f"   - Run: uv run python -m print3d.pipeline {image_path}")
    else:
        print("\n❌ Image generation failed")

if __name__ == "__main__":
    main()