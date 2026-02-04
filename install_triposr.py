#!/usr/bin/env python3
"""
Install and setup actual TripoSR for production use
"""

import subprocess
import sys
from pathlib import Path
import os

def install_triposr_dependencies():
    """Install TripoSR specific dependencies"""
    print("📦 Installing TripoSR dependencies...")
    
    try:
        # Install additional requirements
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "rembg",  # Background removal
            "imageio[ffmpeg]",  # Video/image IO
            "moderngl",  # OpenGL rendering
            "git+https://github.com/tatsy/torchmcubes.git",  # Marching cubes
        ], check=True)
        
        print("✅ Dependencies installed")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def download_triposr_model():
    """Download TripoSR model weights"""
    print("🔽 Downloading TripoSR model...")
    
    try:
        from huggingface_hub import snapshot_download
        
        # Download the model
        model_path = snapshot_download(
            repo_id="stabilityai/TripoSR",
            cache_dir="./models"
        )
        
        print(f"✅ Model downloaded to: {model_path}")
        return model_path
        
    except Exception as e:
        print(f"❌ Failed to download model: {e}")
        return None

def create_triposr_wrapper():
    """Create a simple wrapper for TripoSR"""
    
    wrapper_code = '''
import torch
import numpy as np
from PIL import Image
from pathlib import Path
import sys
import os

# Add the local-3d directory to Python path
local_3d_path = Path(__file__).parent / "local-3d"
sys.path.insert(0, str(local_3d_path))

try:
    from tsr.system import TSR
    from tsr.utils import remove_background, resize_foreground, to_gradio_3d_orientation
    TRIPOSR_AVAILABLE = True
except ImportError:
    TRIPOSR_AVAILABLE = False

class LocalTripoSR:
    def __init__(self):
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        self.model = None
        
    def load_model(self, model_path="./models"):
        """Load TripoSR model"""
        if not TRIPOSR_AVAILABLE:
            raise ImportError("TripoSR not available. Please install dependencies.")
            
        try:
            self.model = TSR.from_pretrained(
                "stabilityai/TripoSR",
                config_name="config.yaml",
                weight_name="model.ckpt"
            )
            self.model.to(self.device)
            print(f"✅ TripoSR loaded on {self.device}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            return False
    
    def image_to_3d(self, image_path, output_path="output/mesh.obj", remove_bg=True):
        """Convert single image to 3D mesh"""
        if self.model is None:
            if not self.load_model():
                return None
        
        try:
            # Load and preprocess image
            image = Image.open(image_path)
            
            if remove_bg:
                image = remove_background(image, "cuda" if torch.cuda.is_available() else "cpu")
            
            image = resize_foreground(image, 0.85)
            image = np.array(image).astype(np.float32) / 255.0
            image = image[:, :, :3] * image[:, :, 3:4] + (1 - image[:, :, 3:4]) * 0.5
            image = Image.fromarray((image * 255.0).astype(np.uint8))
            
            # Generate 3D mesh
            with torch.no_grad():
                scene_codes = self.model([image], device=self.device)
                mesh = self.model.extract_mesh(scene_codes)[0]
                mesh = to_gradio_3d_orientation(mesh)
            
            # Save mesh
            mesh.export(output_path)
            print(f"✅ 3D mesh saved: {output_path}")
            
            return {
                "success": True,
                "output_path": output_path,
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces)
            }
            
        except Exception as e:
            print(f"❌ Error during conversion: {e}")
            return {"success": False, "error": str(e)}

def test_conversion():
    """Test the conversion"""
    triposr = LocalTripoSR()
    
    # Test with existing image
    test_image = "output/test-robot.png"
    if Path(test_image).exists():
        result = triposr.image_to_3d(test_image)
        return result
    else:
        print("No test image found")
        return None

if __name__ == "__main__":
    result = test_conversion()
    if result and result["success"]:
        print("🎉 TripoSR working!")
    else:
        print("⚠️ Setup incomplete")
'''
    
    wrapper_path = Path("print3d/triposr_wrapper.py")
    with open(wrapper_path, 'w') as f:
        f.write(wrapper_code)
    
    print(f"✅ Wrapper created: {wrapper_path}")

def main():
    print("🚀 Installing TripoSR for M4 Mac Mini")
    print("=" * 50)
    
    # Install dependencies
    if not install_triposr_dependencies():
        print("❌ Dependency installation failed")
        return
    
    # Download model
    model_path = download_triposr_model()
    if not model_path:
        print("❌ Model download failed")
        return
    
    # Create wrapper
    create_triposr_wrapper()
    
    print("\n✅ TripoSR installation complete!")
    print("🎯 Ready for local 2D→3D conversion")

if __name__ == "__main__":
    main()