#!/usr/bin/env python3
"""
Simple 3D Pipeline Runner

Usage:
    python run_pipeline.py "a robot warrior"
    python run_pipeline.py "cute dragon" --style miniature
    python run_pipeline.py "geometric vase" --style object --no-meshy
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Add current dir to path
sys.path.insert(0, str(Path(__file__).parent))

from prompt_engineer import enhance_prompt, PrintStyle


def run_image_generation(enhanced_prompt: str, output_path: str) -> bool:
    """Generate image using nano-banana-pro."""
    skill_path = "/Users/pedrohernandezbaez/Documents/moltbot-2026.1.24/skills/nano-banana-pro"
    
    cmd = [
        "uv", "run",
        f"{skill_path}/scripts/generate_image.py",
        "--prompt", enhanced_prompt,
        "--filename", output_path,
        "--resolution", "2K"
    ]
    
    print(f"🎨 Generating image...")
    print(f"   Prompt: {enhanced_prompt[:100]}...")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0 and Path(output_path).exists():
        size_kb = Path(output_path).stat().st_size / 1024
        print(f"✅ Image saved: {output_path} ({size_kb:.1f}KB)")
        return True
    else:
        print(f"❌ Image generation failed: {result.stderr}")
        return False


def run_meshy_conversion(image_path: str, output_dir: str) -> dict:
    """Convert image to 3D using Meshy API."""
    import httpx
    import base64
    import os
    import time
    
    # Load API key
    env_path = Path(__file__).parent / '.env'
    api_key = None
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith('MESHY_API_KEY='):
                api_key = line.split('=', 1)[1].strip()
                break
    
    if not api_key:
        return {"success": False, "error": "MESHY_API_KEY not found in .env"}
    
    # Load and encode image
    print(f"🧊 Converting to 3D with Meshy...")
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    image_b64 = base64.b64encode(image_data).decode('utf-8')
    image_url = f"data:image/png;base64,{image_b64}"
    
    # Create task
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            'https://api.meshy.ai/openapi/v1/image-to-3d',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'image_url': image_url,
                'topology': 'triangle',
                'target_polycount': 30000,
                'ai_model': 'meshy-6',
                'enable_pbr': True,
            },
        )
        
        if response.status_code not in (200, 202):
            return {"success": False, "error": f"API error: {response.text}"}
        
        task_id = response.json().get('result')
        print(f"   Task ID: {task_id}")
    
    # Poll for completion
    start_time = time.time()
    max_wait = 300
    
    with httpx.Client(timeout=30.0) as client:
        while time.time() - start_time < max_wait:
            time.sleep(5)
            
            response = client.get(
                f'https://api.meshy.ai/openapi/v1/image-to-3d/{task_id}',
                headers={'Authorization': f'Bearer {api_key}'},
            )
            
            data = response.json()
            status = data.get('status', 'UNKNOWN')
            progress = data.get('progress', 0)
            
            print(f"\r   Progress: {progress}%", end="", flush=True)
            
            if status == 'SUCCEEDED':
                print(f"\n✅ 3D conversion complete! ({time.time() - start_time:.0f}s)")
                
                # Download GLB
                model_urls = data.get('model_urls', {})
                glb_url = model_urls.get('glb')
                
                if glb_url:
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    output_path = Path(output_dir) / f"model_{timestamp}.glb"
                    
                    dl_response = client.get(glb_url)
                    output_path.write_bytes(dl_response.content)
                    
                    size_kb = output_path.stat().st_size / 1024
                    print(f"✅ Model saved: {output_path} ({size_kb:.1f}KB)")
                    
                    # Also download thumbnail
                    thumb_url = data.get('thumbnail_url')
                    if thumb_url:
                        thumb_path = Path(output_dir) / f"preview_{timestamp}.png"
                        thumb_response = client.get(thumb_url)
                        thumb_path.write_bytes(thumb_response.content)
                        print(f"🖼️  Preview: {thumb_path}")
                    
                    return {
                        "success": True,
                        "model_path": str(output_path),
                        "thumbnail_path": str(thumb_path) if thumb_url else None,
                        "model_urls": model_urls,
                        "task_id": task_id,
                    }
                
                return {"success": False, "error": "No GLB URL in response"}
            
            elif status == 'FAILED':
                print(f"\n❌ Meshy conversion failed")
                return {"success": False, "error": "Conversion failed", "data": data}
    
    print(f"\n❌ Timeout after {max_wait}s")
    return {"success": False, "error": "Timeout"}


def main():
    parser = argparse.ArgumentParser(description="3D Printing Pipeline")
    parser.add_argument("prompt", help="What to create (e.g., 'a robot warrior')")
    parser.add_argument("--style", default="figurine", 
                       choices=["figurine", "miniature", "sculpture", "toy", "bust", "prop", "object", "jewelry", "mechanical"],
                       help="Style of 3D print")
    parser.add_argument("--no-meshy", action="store_true", help="Skip Meshy conversion (image only)")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    
    args = parser.parse_args()
    
    # Setup
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    print("=" * 60)
    print("🏭 3D PRINTING PIPELINE")
    print("=" * 60)
    print(f"Input: {args.prompt}")
    print(f"Style: {args.style}")
    print("=" * 60)
    
    # Phase 1: Enhance prompt
    print("\n📝 Phase 1: Prompt Engineering")
    print("-" * 40)
    
    style_map = {
        "figurine": PrintStyle.FIGURINE,
        "miniature": PrintStyle.MINIATURE,
        "sculpture": PrintStyle.SCULPTURE,
        "toy": PrintStyle.TOY,
        "bust": PrintStyle.BUST,
        "prop": PrintStyle.PROP,
        "object": PrintStyle.OBJECT,
        "jewelry": PrintStyle.JEWELRY,
        "mechanical": PrintStyle.MECHANICAL,
    }
    
    result = enhance_prompt(args.prompt, style=style_map[args.style])
    enhanced_prompt = result["prompt"]
    print(f"Enhanced prompt:\n{enhanced_prompt[:200]}...")
    
    # Phase 2: Generate image
    print("\n🎨 Phase 2: Image Generation")
    print("-" * 40)
    
    image_path = output_dir / f"img_{timestamp}_{args.style}.png"
    if not run_image_generation(enhanced_prompt, str(image_path)):
        print("❌ Pipeline failed at image generation")
        return 1
    
    if args.no_meshy:
        print("\n✅ Pipeline complete (image only)")
        print(f"   Output: {image_path}")
        return 0
    
    # Phase 3: Convert to 3D
    print("\n🧊 Phase 3: 3D Conversion")
    print("-" * 40)
    
    mesh_result = run_meshy_conversion(str(image_path), str(output_dir))
    
    if not mesh_result["success"]:
        print(f"❌ Pipeline failed at 3D conversion: {mesh_result.get('error')}")
        return 1
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE!")
    print("=" * 60)
    print(f"📸 Image: {image_path}")
    print(f"🧊 Model: {mesh_result['model_path']}")
    if mesh_result.get('thumbnail_path'):
        print(f"🖼️  Preview: {mesh_result['thumbnail_path']}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
