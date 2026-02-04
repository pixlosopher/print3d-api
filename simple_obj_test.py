#!/usr/bin/env python3
"""
Generate simple, clean OBJ files for testing
"""

import numpy as np
from pathlib import Path
import time

def create_simple_cube():
    """Create a simple, clean cube OBJ"""
    
    # Clean cube vertices
    vertices = [
        # Bottom face
        [-1, -1, -1],  # 0
        [ 1, -1, -1],  # 1
        [ 1,  1, -1],  # 2
        [-1,  1, -1],  # 3
        # Top face
        [-1, -1,  1],  # 4
        [ 1, -1,  1],  # 5
        [ 1,  1,  1],  # 6
        [-1,  1,  1],  # 7
    ]
    
    # Proper cube faces (counter-clockwise)
    faces = [
        # Bottom face
        [1, 3, 2], [1, 4, 3],
        # Top face  
        [5, 6, 7], [5, 7, 8],
        # Front face
        [1, 2, 6], [1, 6, 5],
        # Back face
        [4, 7, 3], [4, 8, 7],
        # Left face
        [4, 3, 7], [4, 7, 8],
        # Right face
        [1, 5, 6], [1, 6, 2],
    ]
    
    obj_content = """# Simple test cube
# 8 vertices, 12 faces

"""
    
    # Add vertices
    for i, (x, y, z) in enumerate(vertices):
        obj_content += f"v {x:.6f} {y:.6f} {z:.6f}\n"
    
    obj_content += "\n"
    
    # Add faces (OBJ is 1-indexed)
    for face in faces:
        obj_content += f"f {face[0]} {face[1]} {face[2]}\n"
    
    return obj_content

def create_simple_pyramid():
    """Create a simple pyramid"""
    
    vertices = [
        # Base vertices
        [-1, -1, 0],  # 0
        [ 1, -1, 0],  # 1
        [ 1,  1, 0],  # 2
        [-1,  1, 0],  # 3
        # Apex
        [ 0,  0, 2],  # 4
    ]
    
    faces = [
        # Base (looking up from bottom)
        [1, 2, 3], [1, 3, 4],
        # Sides
        [1, 5, 2],
        [2, 5, 3],
        [3, 5, 4],
        [4, 5, 1],
    ]
    
    obj_content = """# Simple test pyramid
# 5 vertices, 6 faces

"""
    
    for i, (x, y, z) in enumerate(vertices):
        obj_content += f"v {x:.6f} {y:.6f} {z:.6f}\n"
    
    obj_content += "\n"
    
    for face in faces:
        obj_content += f"f {face[0]} {face[1]} {face[2]}\n"
    
    return obj_content

def create_image_based_simple_mesh():
    """Create a simple but realistic mesh based on an image"""
    
    print("🎨 Creating simple image-based mesh...")
    
    # Create a simple relief surface
    resolution = 10  # Much lower resolution
    size = 2.0
    
    vertices = []
    faces = []
    
    # Create a grid of vertices
    for i in range(resolution):
        for j in range(resolution):
            x = (i / (resolution - 1)) * size - size/2
            y = (j / (resolution - 1)) * size - size/2
            
            # Simple height function (like a gentle hill)
            distance_from_center = np.sqrt(x*x + y*y)
            z = max(0, 1 - distance_from_center/2) * 0.5
            
            vertices.append([x, y, z])
    
    # Create faces
    for i in range(resolution - 1):
        for j in range(resolution - 1):
            # Bottom-left triangle
            v1 = i * resolution + j + 1        # +1 for OBJ 1-indexing
            v2 = i * resolution + (j + 1) + 1
            v3 = (i + 1) * resolution + j + 1
            
            # Top-right triangle  
            v4 = i * resolution + (j + 1) + 1
            v5 = (i + 1) * resolution + (j + 1) + 1
            v6 = (i + 1) * resolution + j + 1
            
            faces.extend([[v1, v2, v3], [v4, v5, v6]])
    
    obj_content = f"""# Simple relief mesh
# {len(vertices)} vertices, {len(faces)} faces

"""
    
    for x, y, z in vertices:
        obj_content += f"v {x:.6f} {y:.6f} {z:.6f}\n"
    
    obj_content += "\n"
    
    for face in faces:
        obj_content += f"f {face[0]} {face[1]} {face[2]}\n"
    
    return obj_content

def test_simple_objects():
    """Generate and test simple objects"""
    
    print("🧪 Creating Simple Test Objects")
    print("=" * 40)
    
    Path("output").mkdir(exist_ok=True)
    
    # Test 1: Simple cube
    print("1. Creating simple cube...")
    cube_obj = create_simple_cube()
    cube_path = "output/test_cube.obj"
    with open(cube_path, 'w') as f:
        f.write(cube_obj)
    
    print(f"   ✅ Saved: {cube_path}")
    
    # Test 2: Simple pyramid
    print("2. Creating simple pyramid...")
    pyramid_obj = create_simple_pyramid()
    pyramid_path = "output/test_pyramid.obj"
    with open(pyramid_path, 'w') as f:
        f.write(pyramid_obj)
    
    print(f"   ✅ Saved: {pyramid_path}")
    
    # Test 3: Simple relief mesh
    print("3. Creating simple relief mesh...")
    relief_obj = create_image_based_simple_mesh()
    relief_path = "output/test_relief.obj"
    with open(relief_path, 'w') as f:
        f.write(relief_obj)
    
    print(f"   ✅ Saved: {relief_path}")
    
    print(f"\n🎯 Test Results:")
    
    for name, path in [("Cube", cube_path), ("Pyramid", pyramid_path), ("Relief", relief_path)]:
        file_path = Path(path)
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            with open(file_path) as f:
                lines = len(f.readlines())
            
            print(f"   📄 {name}: {size_kb:.1f}KB, {lines} lines")
        
    print(f"\n🚀 All test objects created!")
    print(f"   Try opening these in your 3D viewer - they should be clean and simple!")
    
    return [cube_path, pyramid_path, relief_path]

if __name__ == "__main__":
    test_simple_objects()