#!/usr/bin/env python3
"""
Test the enhanced 3D pipeline with simplified imports
"""

import sys
from pathlib import Path
import json
import time
from datetime import datetime
import subprocess

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def generate_image(prompt, style="figurine", output_dir="./output"):
    """Generate image using nano-banana-pro skill"""
    print("🎨 Phase 1: Image Generation")
    print("-" * 30)
    
    style_prompts = {
        "figurine": "figurine style, toy miniature, simple clean design, solid object",
        "sculpture": "sculpture style, artistic form, solid material, museum piece",
        "object": "functional object, product design, clean lines",
        "character": "character design, game figure, collectible toy"
    }
    
    enhanced_prompt = f"{prompt}, {style_prompts.get(style, style_prompts['figurine'])}, white background, perfect for 3D printing"
    
    skill_path = "/Users/pedrohernandezbaez/Documents/moltbot-2026.1.24/skills/nano-banana-pro"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = f"{output_dir}/{timestamp}-{style}.png"
    
    Path(output_dir).mkdir(exist_ok=True)
    
    print(f"🍌 Generating: {enhanced_prompt}")
    
    cmd = [
        "uv", "run", 
        f"{skill_path}/scripts/generate_image.py",
        "--prompt", enhanced_prompt,
        "--filename", output_path,
        "--resolution", "1K"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Image generated: {output_path}")
            return {"success": True, "path": output_path, "prompt": enhanced_prompt}
        else:
            print(f"❌ Image generation failed: {result.stderr}")
            return {"success": False, "error": result.stderr}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}

def generate_mesh_local(image_path, output_dir="./output"):
    """Generate 3D mesh using local method"""
    print("\n🧊 Phase 2: 3D Mesh Generation")
    print("-" * 30)
    
    try:
        from local_mesh_gen import LocalMeshGenerator
        
        generator = LocalMeshGenerator()
        print(f"🔧 Device: {generator.device}")
        print(f"🔧 TripoSR Available: {generator.is_available()}")
        
        if generator.is_available():
            print("🚀 Using real TripoSR...")
            result = generator.from_image(image_path, output_dir)
        else:
            print("🎭 Using simulation...")
            result = generator.simulate_conversion(image_path, output_dir)
        
        if result.success:
            print(f"✅ Mesh generated: {result.local_path}")
            print(f"  📊 {result.vertices} vertices, {result.faces} faces")
            print(f"  ⏱️ {result.processing_time:.1f}s on {result.device_used}")
            
            return {
                "success": True,
                "path": str(result.local_path),
                "vertices": result.vertices,
                "faces": result.faces,
                "time": result.processing_time,
                "device": result.device_used,
                "metadata": result.metadata
            }
        else:
            print(f"❌ Mesh generation failed: {result.error}")
            return {"success": False, "error": result.error}
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return {"success": False, "error": f"Import error: {e}"}

def estimate_costs(mesh_path, size_mm=50.0):
    """Estimate printing costs"""
    print(f"\n💰 Phase 3: Print Cost Estimation")
    print("-" * 30)
    
    volume_cm3 = (size_mm / 10) ** 3
    
    materials = {
        "PLA Plastic": {"rate": 0.05, "base": 5.00, "days": "7-14", "quality": "Good"},
        "Resin (Detail)": {"rate": 0.15, "base": 8.00, "days": "7-14", "quality": "Excellent"}, 
        "Nylon": {"rate": 0.12, "base": 12.00, "days": "10-16", "quality": "Durable"},
        "Steel": {"rate": 2.50, "base": 25.00, "days": "14-21", "quality": "Premium"}
    }
    
    pricing = {}
    for material, data in materials.items():
        total = data["base"] + (volume_cm3 * data["rate"])
        pricing[material] = {
            "price": round(total, 2),
            "shipping": data["days"],
            "quality": data["quality"]
        }
        print(f"💳 {material}: ${pricing[material]['price']} ({pricing[material]['shipping']})")
    
    cheapest = min(pricing.items(), key=lambda x: x[1]["price"])
    print(f"🏆 Best value: {cheapest[0]} at ${cheapest[1]['price']}")
    
    return {
        "success": True,
        "size_mm": size_mm,
        "volume_cm3": round(volume_cm3, 2),
        "pricing": pricing,
        "best": {"material": cheapest[0], **cheapest[1]}
    }

def run_pipeline(prompt, style="figurine", size_mm=50.0):
    """Run complete pipeline"""
    print("🚀 Enhanced 3D Pipeline Test")
    print("=" * 50)
    print(f"📝 Creating: {prompt}")
    print(f"🎭 Style: {style}")
    print(f"📐 Size: {size_mm}mm")
    
    start_time = time.time()
    
    # Phase 1: Image
    image_result = generate_image(prompt, style)
    if not image_result["success"]:
        return image_result
    
    # Phase 2: Mesh  
    mesh_result = generate_mesh_local(image_result["path"])
    if not mesh_result["success"]:
        return mesh_result
    
    # Phase 3: Costs
    cost_result = estimate_costs(mesh_result["path"], size_mm)
    
    total_time = time.time() - start_time
    
    # Compile results
    result = {
        "status": "success",
        "total_time": round(total_time, 1),
        "prompt": prompt,
        "style": style,
        "size_mm": size_mm,
        "files": {
            "image": image_result["path"],
            "mesh": mesh_result["path"]
        },
        "mesh_stats": {
            "vertices": mesh_result["vertices"],
            "faces": mesh_result["faces"],
            "generation_time": mesh_result["time"],
            "device": mesh_result["device"]
        },
        "pricing": cost_result["pricing"],
        "best_option": cost_result["best"]
    }
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    results_file = f"output/enhanced_pipeline_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n🎯 Pipeline Complete!")
    print(f"  ⏱️ Total time: {total_time:.1f}s")
    print(f"  🖼️ Image: {result['files']['image']}")  
    print(f"  🧊 Mesh: {result['files']['mesh']}")
    print(f"  💰 Best price: {result['best_option']['material']} (${result['best_option']['price']})")
    print(f"  📋 Results: {results_file}")
    
    return result

def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", help="What to create")
    parser.add_argument("--style", default="figurine", help="Style")
    parser.add_argument("--size", type=float, default=50.0, help="Size in mm")
    
    args = parser.parse_args()
    
    result = run_pipeline(args.prompt, args.style, args.size)
    
    if result["status"] == "success":
        print(f"\n✅ SUCCESS! All files in output/ directory")
    else:
        print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()