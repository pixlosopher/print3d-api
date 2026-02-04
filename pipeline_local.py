#!/usr/bin/env python3
"""
Enhanced 3D Pipeline with Local Generation Support
Integrates both paid APIs and free local alternatives
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
import time

try:
    from .image_gen import ImageGenerator
    from .local_mesh_gen import LocalMeshGenerator
    from .print_api import PrintService
    from .config import Config
except ImportError:
    from image_gen import ImageGenerator
    from local_mesh_gen import LocalMeshGenerator
    from print_api import PrintService
    from config import Config

class EnhancedPipeline:
    """Enhanced 3D pipeline with local and cloud options."""
    
    def __init__(self, output_dir="./output", prefer_local=True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.prefer_local = prefer_local
        
        # Initialize components
        self.image_gen = ImageGenerator()
        self.local_mesh_gen = LocalMeshGenerator()
        self.config = Config()
        
    def generate_image(self, prompt: str, style: str = "figurine") -> dict:
        """Generate image optimized for 3D printing."""
        print("🎨 Phase 1: Image Generation")
        print("-" * 30)
        
        style_prompts = {
            "figurine": "figurine style, toy miniature, simple clean design, solid object",
            "sculpture": "sculpture style, artistic form, solid material, museum piece", 
            "object": "functional object, product design, clean lines",
            "character": "character design, game figure, collectible toy"
        }
        
        enhanced_prompt = f"{prompt}, {style_prompts.get(style, style_prompts['figurine'])}, white background, perfect for 3D printing"
        
        try:
            result = self.image_gen.generate(enhanced_prompt, style)
            print(f"✅ Image generated: {result.local_path}")
            return {"success": True, "image_result": result}
        except Exception as e:
            print(f"❌ Image generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_mesh(self, image_path: str, method: str = "auto") -> dict:
        """Generate 3D mesh from image."""
        print("\n🧊 Phase 2: 3D Mesh Generation")
        print("-" * 30)
        
        if method == "auto":
            # Choose best available method
            if self.prefer_local and self.local_mesh_gen.is_available():
                method = "local"
            elif self.config.meshy_api_key:
                method = "meshy"
            else:
                method = "simulate"
        
        print(f"🔧 Using method: {method}")
        
        if method == "local":
            result = self.local_mesh_gen.from_image(image_path, self.output_dir)
        elif method == "simulate":
            result = self.local_mesh_gen.simulate_conversion(image_path, self.output_dir)
        elif method == "meshy":
            print("⚠️ Meshy API integration not implemented in this version")
            result = self.local_mesh_gen.simulate_conversion(image_path, self.output_dir)
        else:
            return {"success": False, "error": f"Unknown method: {method}"}
        
        if result.success:
            print(f"✅ 3D mesh generated: {result.local_path}")
            print(f"  📊 {result.vertices} vertices, {result.faces} faces")
            print(f"  ⏱️ Processing time: {result.processing_time:.1f}s")
        
        return {"success": result.success, "mesh_result": result}
    
    def estimate_printing_cost(self, mesh_path: str, size_mm: float = 50.0) -> dict:
        """Estimate 3D printing costs."""
        print(f"\n💰 Phase 3: Print Cost Estimation")
        print("-" * 30)
        
        # Volume estimation (rough)
        volume_cm3 = (size_mm / 10) ** 3
        
        material_costs = {
            "PLA Plastic": {
                "cost_per_cm3": 0.05,
                "base_cost": 5.00,
                "shipping_days": "7-14",
                "quality": "Good"
            },
            "Resin (High Detail)": {
                "cost_per_cm3": 0.15, 
                "base_cost": 8.00,
                "shipping_days": "7-14",
                "quality": "Excellent"
            },
            "Nylon (Durable)": {
                "cost_per_cm3": 0.12,
                "base_cost": 12.00,
                "shipping_days": "10-16",
                "quality": "Very Durable"
            },
            "Metal (Steel)": {
                "cost_per_cm3": 2.50,
                "base_cost": 25.00,
                "shipping_days": "14-21",
                "quality": "Premium"
            }
        }
        
        pricing = {}
        for material, data in material_costs.items():
            total_cost = data["base_cost"] + (volume_cm3 * data["cost_per_cm3"])
            pricing[material] = {
                "price_usd": round(total_cost, 2),
                "shipping": data["shipping_days"],
                "quality": data["quality"],
                "volume_cm3": round(volume_cm3, 2)
            }
            
            print(f"💳 {material}: ${pricing[material]['price_usd']} ({pricing[material]['shipping']} days)")
        
        cheapest = min(pricing.items(), key=lambda x: x[1]["price_usd"])
        print(f"🏆 Cheapest option: {cheapest[0]} at ${cheapest[1]['price_usd']}")
        
        return {
            "success": True,
            "size_mm": size_mm,
            "volume_cm3": round(volume_cm3, 2), 
            "pricing": pricing,
            "cheapest": {"material": cheapest[0], **cheapest[1]}
        }
    
    def run_full_pipeline(self, prompt: str, style: str = "figurine", size_mm: float = 50.0, mesh_method: str = "auto"):
        """Run the complete pipeline."""
        
        print("🚀 Enhanced 3D Pipeline")
        print("=" * 50)
        print(f"📝 Prompt: {prompt}")
        print(f"🎭 Style: {style}")
        print(f"📐 Size: {size_mm}mm")
        print(f"🔧 Mesh method: {mesh_method}")
        print(f"💻 Local available: {self.local_mesh_gen.is_available()}")
        print(f"🌐 API available: {bool(self.config.meshy_api_key)}")
        
        start_time = time.time()
        
        # Phase 1: Generate Image
        image_result = self.generate_image(prompt, style)
        if not image_result["success"]:
            return image_result
        
        image_path = image_result["image_result"].local_path
        
        # Phase 2: Generate Mesh
        mesh_result = self.generate_mesh(str(image_path), mesh_method)
        if not mesh_result["success"]:
            return mesh_result
        
        mesh_path = mesh_result["mesh_result"].local_path
        
        # Phase 3: Estimate Costs
        cost_result = self.estimate_printing_cost(str(mesh_path), size_mm)
        
        # Compile final result
        total_time = time.time() - start_time
        
        result = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total_time": round(total_time, 1),
            "input": {
                "prompt": prompt,
                "style": style, 
                "size_mm": size_mm,
                "mesh_method": mesh_method
            },
            "image": {
                "path": str(image_path),
                "prompt": image_result["image_result"].prompt,
                "url": image_result["image_result"].url
            },
            "mesh": {
                "path": str(mesh_path),
                "vertices": mesh_result["mesh_result"].vertices,
                "faces": mesh_result["mesh_result"].faces,
                "processing_time": mesh_result["mesh_result"].processing_time,
                "method": mesh_method,
                "device": mesh_result["mesh_result"].device_used
            },
            "pricing": cost_result["pricing"],
            "cheapest_option": cost_result["cheapest"]
        }
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        results_file = self.output_dir / f"pipeline_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n🎯 Pipeline Complete!")
        print(f"  ⏱️ Total time: {total_time:.1f}s")
        print(f"  🖼️ Image: {image_path}")
        print(f"  🧊 Mesh: {mesh_path}")
        print(f"  💰 Cheapest: {result['cheapest_option']['material']} (${result['cheapest_option']['price_usd']})")
        print(f"  📋 Results: {results_file}")
        
        return result

def main():
    parser = argparse.ArgumentParser(description="Enhanced 3D Pipeline with Local Generation")
    parser.add_argument("prompt", help="What to create")
    parser.add_argument("--style", choices=["figurine", "sculpture", "object", "character"],
                       default="figurine", help="3D printing style")
    parser.add_argument("--size", type=float, default=50.0, help="Size in millimeters")
    parser.add_argument("--method", choices=["auto", "local", "meshy", "simulate"],
                       default="auto", help="3D generation method")
    parser.add_argument("--prefer-cloud", action="store_true",
                       help="Prefer cloud APIs over local generation")
    
    args = parser.parse_args()
    
    pipeline = EnhancedPipeline(prefer_local=not args.prefer_cloud)
    
    try:
        result = pipeline.run_full_pipeline(
            prompt=args.prompt,
            style=args.style,
            size_mm=args.size,
            mesh_method=args.method
        )
        
        if result["status"] == "success":
            print(f"\n✅ SUCCESS! Check output folder for files.")
        else:
            print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")
            
    except KeyboardInterrupt:
        print(f"\n⏸️ Pipeline interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")

if __name__ == "__main__":
    main()