#!/usr/bin/env python3
"""
Ultra-simple mesh generator - basic shapes that WILL work
"""

from PIL import Image
import numpy as np
from pathlib import Path

def create_basic_relief_from_image(image_path, output_path="output/basic_relief.obj"):
    """Create the simplest possible relief mesh from an image"""
    
    print(f"🔨 Creating BASIC relief from: {image_path}")
    
    # Load and process image
    image = Image.open(image_path).convert('L')  # Grayscale
    
    # Resize to VERY small resolution
    small_size = 20  # Super tiny grid
    image = image.resize((small_size, small_size), Image.Resampling.LANCZOS)
    
    img_array = np.array(image) / 255.0  # Normalize to 0-1
    
    print(f"  📐 Grid: {small_size}x{small_size}")
    print(f"  📊 Height range: {img_array.min():.3f} - {img_array.max():.3f}")
    
    # Create very simple vertices
    vertices = []
    
    for i in range(small_size):
        for j in range(small_size):
            x = (j - small_size/2) * 0.2  # Scale to reasonable size
            y = (i - small_size/2) * 0.2
            z = img_array[i, j] * 0.5      # Height from image
            
            vertices.append([x, y, z])
    
    # Create faces - only connect adjacent vertices
    faces = []
    
    for i in range(small_size - 1):
        for j in range(small_size - 1):
            # Get vertex indices (1-based for OBJ)
            bottom_left  = (i * small_size + j) + 1
            bottom_right = (i * small_size + j + 1) + 1
            top_left     = ((i + 1) * small_size + j) + 1
            top_right    = ((i + 1) * small_size + j + 1) + 1
            
            # Two triangles per square
            faces.append([bottom_left, bottom_right, top_left])
            faces.append([bottom_right, top_right, top_left])
    
    # Write OBJ file
    Path(output_path).parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(f"# Basic relief mesh from {image_path}\n")
        f.write(f"# {len(vertices)} vertices, {len(faces)} faces\n\n")
        
        # Write vertices
        for vertex in vertices:
            f.write(f"v {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
        
        f.write("\n")
        
        # Write faces
        for face in faces:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")
    
    file_size = Path(output_path).stat().st_size / 1024
    
    print(f"✅ Basic relief created!")
    print(f"  📄 File: {output_path}")
    print(f"  📊 {len(vertices)} vertices, {len(faces)} faces")
    print(f"  💾 Size: {file_size:.1f}KB")
    
    return output_path

def create_test_shapes():
    """Create multiple test shapes to verify what works"""
    
    print("🧪 Creating Ultra-Simple Test Shapes")
    print("=" * 45)
    
    results = []
    
    # 1. Tiny cube
    print("1. Creating tiny cube...")
    cube_path = "output/tiny_cube.obj"
    with open(cube_path, 'w') as f:
        f.write("""# Tiny test cube
v -0.5 -0.5 -0.5
v  0.5 -0.5 -0.5
v  0.5  0.5 -0.5
v -0.5  0.5 -0.5
v -0.5 -0.5  0.5
v  0.5 -0.5  0.5
v  0.5  0.5  0.5
v -0.5  0.5  0.5

f 1 2 3
f 1 3 4
f 5 8 7
f 5 7 6
f 1 5 6
f 1 6 2
f 2 6 7
f 2 7 3
f 3 7 8
f 3 8 4
f 5 1 4
f 5 4 8
""")
    
    size = Path(cube_path).stat().st_size / 1024
    print(f"   ✅ Tiny cube: {size:.1f}KB")
    results.append(cube_path)
    
    # 2. Simple triangle
    print("2. Creating single triangle...")
    triangle_path = "output/single_triangle.obj"
    with open(triangle_path, 'w') as f:
        f.write("""# Single triangle test
v -1.0  0.0  0.0
v  1.0  0.0  0.0
v  0.0  1.0  0.5

f 1 2 3
""")
    
    size = Path(triangle_path).stat().st_size / 1024
    print(f"   ✅ Single triangle: {size:.1f}KB")
    results.append(triangle_path)
    
    # 3. Basic relief if image exists
    test_images = [
        "output/img_20260131-225655_character.png",
        "output/test-robot.png"
    ]
    
    for img_path in test_images:
        if Path(img_path).exists():
            print("3. Creating basic relief from image...")
            relief_path = create_basic_relief_from_image(img_path)
            results.append(relief_path)
            break
    
    print(f"\n🎯 Created {len(results)} test files")
    for path in results:
        size = Path(path).stat().st_size / 1024
        print(f"   📄 {Path(path).name}: {size:.1f}KB")
    
    return results

if __name__ == "__main__":
    files = create_test_shapes()
    print(f"\n🚀 {len(files)} ultra-simple test files created!")
    print("📋 These should definitely work in any 3D viewer")