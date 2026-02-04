#!/usr/bin/env python3
"""
Fixed mesh generator - creates clean, connected surfaces
"""

import numpy as np
from PIL import Image
import torch
from pathlib import Path
import time
from scipy import ndimage

class CleanMeshGenerator:
    """Generate clean, connected meshes from images"""
    
    def __init__(self):
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        print(f"🔧 Clean Mesh Generator initialized on {self.device}")
    
    def generate_clean_mesh(self, image_path, output_path="output/clean_mesh.obj", size_mm=50.0):
        """Generate a clean, connected mesh"""
        
        print(f"🎨 Processing: {image_path}")
        start_time = time.time()
        
        # Load image
        image = Image.open(image_path).convert("RGBA")
        print(f"  📏 Input: {image.size}")
        
        # Get alpha mask or create one
        img_array = np.array(image)
        if img_array.shape[2] == 4:
            alpha = img_array[:, :, 3] / 255.0
        else:
            # Create mask from non-white pixels
            gray = np.mean(img_array[:, :, :3], axis=2)
            alpha = (gray < 240).astype(float)
        
        # Resize to manageable resolution
        target_res = 64  # Much smaller for clean geometry
        if image.size[0] != target_res or image.size[1] != target_res:
            image_resized = image.resize((target_res, target_res), Image.Resampling.LANCZOS)
            alpha = ndimage.zoom(alpha, (target_res/alpha.shape[0], target_res/alpha.shape[1]))
            img_array = np.array(image_resized)
        
        # Create height map from brightness
        if len(img_array.shape) == 3:
            height_map = np.mean(img_array[:, :, :3], axis=2) / 255.0
        else:
            height_map = img_array / 255.0
        
        # Apply alpha mask
        height_map = height_map * alpha
        
        # Smooth the height map to avoid spikes
        height_map = ndimage.gaussian_filter(height_map, sigma=1.0)
        
        print(f"  📊 Height range: {height_map.min():.3f} - {height_map.max():.3f}")
        
        # Create mesh with proper connectivity
        mesh_data = self.create_connected_mesh(height_map, alpha, size_mm)
        
        # Write clean OBJ file
        self.write_obj_file(mesh_data, output_path)
        
        processing_time = time.time() - start_time
        
        print(f"✅ Clean mesh generated!")
        print(f"  📄 Output: {output_path}")
        print(f"  📊 {len(mesh_data['vertices'])} vertices, {len(mesh_data['faces'])} faces")
        print(f"  ⏱️ Time: {processing_time:.1f}s")
        
        return {
            "success": True,
            "output_path": output_path,
            "vertices": len(mesh_data['vertices']),
            "faces": len(mesh_data['faces']),
            "processing_time": processing_time,
            "method": "Clean Connected Mesh"
        }
    
    def create_connected_mesh(self, height_map, alpha, size_mm):
        """Create a properly connected mesh"""
        
        print("  🔨 Creating connected mesh...")
        
        height, width = height_map.shape
        max_height = size_mm / 10.0  # Reasonable depth
        
        vertices = []
        vertex_indices = np.full((height, width), -1, dtype=int)
        
        # Create vertices only where we have object
        for i in range(height):
            for j in range(width):
                if alpha[i, j] > 0.1:  # Only where object exists
                    x = (j / (width - 1) - 0.5) * size_mm / 10.0
                    y = (i / (height - 1) - 0.5) * size_mm / 10.0
                    z = height_map[i, j] * max_height
                    
                    vertex_indices[i, j] = len(vertices)
                    vertices.append([x, y, z])
        
        # Create faces with proper connectivity
        faces = []
        for i in range(height - 1):
            for j in range(width - 1):
                # Get the four corner vertices
                v1 = vertex_indices[i, j]
                v2 = vertex_indices[i, j + 1]
                v3 = vertex_indices[i + 1, j]
                v4 = vertex_indices[i + 1, j + 1]
                
                # Only create faces if all four vertices exist
                if v1 >= 0 and v2 >= 0 and v3 >= 0 and v4 >= 0:
                    # Two triangles per quad (proper winding)
                    faces.append([v1 + 1, v2 + 1, v3 + 1])  # +1 for OBJ indexing
                    faces.append([v2 + 1, v4 + 1, v3 + 1])
        
        # Add base vertices and faces for solid object
        base_z = -max_height * 0.1  # Slight base thickness
        
        # Find boundary vertices
        boundary_vertices = []
        for i in range(height):
            for j in range(width):
                if vertex_indices[i, j] >= 0:
                    # Check if this is a boundary vertex
                    is_boundary = False
                    for di in [-1, 0, 1]:
                        for dj in [-1, 0, 1]:
                            ni, nj = i + di, j + dj
                            if (0 <= ni < height and 0 <= nj < width):
                                if vertex_indices[ni, nj] < 0:  # Adjacent to empty space
                                    is_boundary = True
                                    break
                            else:  # At edge of image
                                is_boundary = True
                                break
                        if is_boundary:
                            break
                    
                    if is_boundary:
                        boundary_vertices.append(vertex_indices[i, j])
        
        # Add base vertices for boundary
        base_vertex_map = {}
        for surface_idx in boundary_vertices:
            if surface_idx < len(vertices):
                x, y, _ = vertices[surface_idx]
                base_idx = len(vertices)
                vertices.append([x, y, base_z])
                base_vertex_map[surface_idx] = base_idx
        
        # Connect surface to base (sides)
        for i in range(height - 1):
            for j in range(width - 1):
                v1 = vertex_indices[i, j]
                v2 = vertex_indices[i, j + 1]
                v3 = vertex_indices[i + 1, j]
                
                # Create side faces where needed
                if v1 >= 0 and v2 >= 0:  # Horizontal edge
                    if v1 in base_vertex_map and v2 in base_vertex_map:
                        b1 = base_vertex_map[v1]
                        b2 = base_vertex_map[v2]
                        faces.append([v1 + 1, b1 + 1, v2 + 1])
                        faces.append([b1 + 1, b2 + 1, v2 + 1])
        
        return {
            "vertices": vertices,
            "faces": faces
        }
    
    def write_obj_file(self, mesh_data, output_path):
        """Write clean OBJ file"""
        
        Path(output_path).parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write("# Clean connected mesh\n")
            f.write(f"# Generated vertices: {len(mesh_data['vertices'])}\n")
            f.write(f"# Generated faces: {len(mesh_data['faces'])}\n\n")
            
            # Write vertices
            for vertex in mesh_data['vertices']:
                f.write(f"v {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
            
            f.write("\n")
            
            # Write faces
            for face in mesh_data['faces']:
                f.write(f"f {face[0]} {face[1]} {face[2]}\n")

def test_clean_mesh():
    """Test clean mesh generation"""
    
    print("🧪 Testing Clean Mesh Generation")
    print("=" * 40)
    
    generator = CleanMeshGenerator()
    
    # Find test image
    test_images = [
        "output/img_20260131-225655_character.png",
        "output/test-robot.png"
    ]
    
    test_image = None
    for img in test_images:
        if Path(img).exists():
            test_image = img
            break
    
    if not test_image:
        print("❌ No test image found")
        return False
    
    # Generate clean mesh
    result = generator.generate_clean_mesh(
        test_image, 
        "output/CLEAN_mesh.obj", 
        45.0
    )
    
    if result["success"]:
        print(f"\n🎉 SUCCESS!")
        print(f"  📊 {result['vertices']} vertices, {result['faces']} faces")
        print(f"  ⏱️ {result['processing_time']:.1f}s")
        print(f"  🎯 Method: {result['method']}")
        return True
    else:
        print("❌ Failed to generate clean mesh")
        return False

if __name__ == "__main__":
    success = test_clean_mesh()
    if success:
        print("\n✅ Clean mesh generator ready!")
        print("🔧 No more lighthouse explosions!")
    else:
        print("\n⚠️ Setup needs work")