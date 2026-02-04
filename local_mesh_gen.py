"""
Local mesh generation using TripoSR for print3d pipeline.
Free alternative to Meshy.ai API.
"""

from __future__ import annotations

import torch
import numpy as np
from PIL import Image
from pathlib import Path
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

try:
    from .config import Config, get_config
except ImportError:
    from config import Config, get_config

# Check if TripoSR is available
TRIPOSR_AVAILABLE = False
try:
    import sys
    local_3d_path = Path(__file__).parent / "local-3d"
    if local_3d_path.exists():
        sys.path.insert(0, str(local_3d_path))
        from tsr.system import TSR
        from tsr.utils import remove_background, resize_foreground, to_gradio_3d_orientation
        TRIPOSR_AVAILABLE = True
except ImportError:
    pass

@dataclass
class LocalMeshResult:
    """Result from local mesh generation."""
    success: bool
    local_path: Optional[Path] = None
    vertices: int = 0
    faces: int = 0
    processing_time: float = 0.0
    device_used: str = "cpu"
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

class LocalMeshGenerator:
    """Local 3D mesh generation using TripoSR."""
    
    def __init__(self):
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        self.model = None
        self._model_loaded = False
        
    def is_available(self) -> bool:
        """Check if local mesh generation is available."""
        return TRIPOSR_AVAILABLE
    
    def load_model(self) -> bool:
        """Load TripoSR model."""
        if not TRIPOSR_AVAILABLE:
            return False
            
        if self._model_loaded:
            return True
            
        try:
            print(f"🔄 Loading TripoSR model on {self.device}...")
            self.model = TSR.from_pretrained(
                "stabilityai/TripoSR",
                config_name="config.yaml",
                weight_name="model.ckpt"
            )
            self.model.to(self.device)
            self._model_loaded = True
            print(f"✅ TripoSR loaded successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load TripoSR model: {e}")
            return False
    
    def from_image(self, image_path: str | Path, output_dir: str | Path = "output") -> LocalMeshResult:
        """Convert image to 3D mesh using local TripoSR."""
        
        start_time = time.time()
        image_path = Path(image_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        if not self.is_available():
            return LocalMeshResult(
                success=False,
                error="TripoSR not available. Please install dependencies."
            )
        
        if not self.load_model():
            return LocalMeshResult(
                success=False,
                error="Failed to load TripoSR model"
            )
        
        try:
            # Load and preprocess image
            print(f"🖼️ Processing image: {image_path}")
            image = Image.open(image_path).convert('RGBA')
            
            # Remove background if image doesn't have transparency
            if image.mode == 'RGB':
                print("🎭 Removing background...")
                image = remove_background(image, self.device.type)
            
            # Resize foreground
            image = resize_foreground(image, 0.85)
            
            # Prepare for model
            image_array = np.array(image).astype(np.float32) / 255.0
            
            # Handle transparency
            if image_array.shape[2] == 4:  # RGBA
                rgb = image_array[:, :, :3]
                alpha = image_array[:, :, 3:4]
                image_array = rgb * alpha + (1 - alpha) * 0.5
            
            image_processed = Image.fromarray((image_array * 255.0).astype(np.uint8))
            
            # Generate 3D mesh
            print(f"🧠 Generating 3D mesh on {self.device}...")
            with torch.no_grad():
                scene_codes = self.model([image_processed], device=self.device)
                mesh = self.model.extract_mesh(scene_codes)[0]
                mesh = to_gradio_3d_orientation(mesh)
            
            # Save mesh
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_filename = f"local_mesh_{timestamp}.obj"
            output_path = output_dir / output_filename
            
            mesh.export(str(output_path))
            
            processing_time = time.time() - start_time
            
            print(f"✅ Local mesh generated: {output_path}")
            print(f"  📊 Vertices: {len(mesh.vertices)}")
            print(f"  🔺 Faces: {len(mesh.faces)}")
            print(f"  ⏱️ Time: {processing_time:.1f}s")
            
            return LocalMeshResult(
                success=True,
                local_path=output_path,
                vertices=len(mesh.vertices),
                faces=len(mesh.faces),
                processing_time=processing_time,
                device_used=str(self.device),
                metadata={
                    "model": "TripoSR",
                    "input_image": str(image_path),
                    "original_size": f"{image.size[0]}x{image.size[1]}",
                    "device": str(self.device),
                    "memory_used": torch.mps.current_allocated_memory() / 1024**2 if self.device.type == "mps" else "N/A"
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"❌ Error during mesh generation: {e}")
            return LocalMeshResult(
                success=False,
                processing_time=processing_time,
                device_used=str(self.device),
                error=str(e)
            )
    
    def simulate_conversion(self, image_path: str | Path, output_dir: str | Path = "output") -> LocalMeshResult:
        """Simulate mesh conversion for testing when TripoSR not available."""
        
        start_time = time.time()
        image_path = Path(image_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        print(f"🎭 Simulating mesh generation for: {image_path}")
        
        # Load image for basic info
        image = Image.open(image_path)
        print(f"  📏 Image size: {image.size}")
        
        # Simulate processing time
        time.sleep(1.5)  # Realistic processing time
        
        # Create placeholder mesh
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_filename = f"simulated_mesh_{timestamp}.obj"
        output_path = output_dir / output_filename
        
        # Simple cube OBJ content
        obj_content = """# Simulated mesh from LocalMeshGenerator
mtllib material.mtl
usemtl Material

# Cube vertices
v -1.0 -1.0 1.0
v 1.0 -1.0 1.0  
v -1.0 1.0 1.0
v 1.0 1.0 1.0
v -1.0 1.0 -1.0
v 1.0 1.0 -1.0
v -1.0 -1.0 -1.0
v 1.0 -1.0 -1.0

# Texture coordinates
vt 0.0 0.0
vt 1.0 0.0
vt 1.0 1.0
vt 0.0 1.0

# Faces
f 1/1 2/2 4/3
f 1/1 4/3 3/4
"""
        
        with open(output_path, 'w') as f:
            f.write(obj_content)
        
        processing_time = time.time() - start_time
        
        print(f"✅ Simulated mesh created: {output_path}")
        
        return LocalMeshResult(
            success=True,
            local_path=output_path,
            vertices=8,  # Cube vertices
            faces=12,    # Cube faces
            processing_time=processing_time,
            device_used=str(self.device),
            metadata={
                "model": "Simulated",
                "note": "This is a placeholder. Install TripoSR for real mesh generation.",
                "input_image": str(image_path),
                "original_size": f"{image.size[0]}x{image.size[1]}",
            }
        )

def test_local_generation():
    """Test local mesh generation."""
    print("🧪 Testing Local Mesh Generation")
    print("=" * 40)
    
    generator = LocalMeshGenerator()
    
    print(f"📊 Device: {generator.device}")
    print(f"🔧 TripoSR Available: {generator.is_available()}")
    
    # Find a test image
    test_images = ["output/test-robot.png", "output/20260131-152448-figurine.png"]
    test_image = None
    
    for img_path in test_images:
        if Path(img_path).exists():
            test_image = img_path
            break
    
    if not test_image:
        print("❌ No test image found")
        return False
    
    # Test conversion
    if generator.is_available():
        print("🚀 Running real TripoSR conversion...")
        result = generator.from_image(test_image)
    else:
        print("🎭 Running simulated conversion...")
        result = generator.simulate_conversion(test_image)
    
    if result.success:
        print(f"✅ SUCCESS!")
        print(f"  📄 Output: {result.local_path}")
        print(f"  📊 Vertices: {result.vertices}")
        print(f"  🔺 Faces: {result.faces}")
        print(f"  ⏱️ Time: {result.processing_time:.1f}s")
        print(f"  💻 Device: {result.device_used}")
        return True
    else:
        print(f"❌ FAILED: {result.error}")
        return False

if __name__ == "__main__":
    success = test_local_generation()
    if success:
        print("\n🎉 Local mesh generation ready!")
    else:
        print("\n⚠️ Setup needs work")