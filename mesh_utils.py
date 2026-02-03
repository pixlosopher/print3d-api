"""
Mesh utilities for print3d pipeline.

Provides mesh validation, analysis, and basic manipulation
without requiring heavy dependencies like trimesh.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


@dataclass
class Dimensions:
    """3D bounding box dimensions."""
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float
    
    @property
    def width(self) -> float:
        """X dimension."""
        return self.max_x - self.min_x
    
    @property
    def depth(self) -> float:
        """Y dimension."""
        return self.max_y - self.min_y
    
    @property
    def height(self) -> float:
        """Z dimension."""
        return self.max_z - self.min_z
    
    @property
    def max_dimension(self) -> float:
        """Largest dimension."""
        return max(self.width, self.depth, self.height)
    
    def scale_factor(self, target_height_mm: float) -> float:
        """Calculate scale factor to achieve target height."""
        if self.height == 0:
            return 1.0
        return target_height_mm / self.height
    
    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "depth": self.depth,
            "height": self.height,
            "bounds": {
                "x": [self.min_x, self.max_x],
                "y": [self.min_y, self.max_y],
                "z": [self.min_z, self.max_z],
            }
        }


@dataclass
class MeshInfo:
    """Basic information about a mesh file."""
    path: Path
    format: str
    triangle_count: int
    dimensions: Dimensions | None
    estimated_volume_mm3: float | None
    file_size_bytes: int
    is_binary: bool = True
    
    @property
    def vertex_count_approx(self) -> int:
        """Approximate vertex count (triangles * 3, minus shared)."""
        return self.triangle_count * 3  # Upper bound
    
    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "format": self.format,
            "triangle_count": self.triangle_count,
            "vertex_count_approx": self.vertex_count_approx,
            "dimensions": self.dimensions.to_dict() if self.dimensions else None,
            "estimated_volume_mm3": self.estimated_volume_mm3,
            "file_size_bytes": self.file_size_bytes,
            "is_binary": self.is_binary,
        }


@dataclass
class ValidationResult:
    """Result of mesh validation."""
    is_valid: bool
    issues: list[str]
    warnings: list[str]
    info: MeshInfo | None
    
    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "issues": self.issues,
            "warnings": self.warnings,
            "info": self.info.to_dict() if self.info else None,
        }


def _read_binary_stl(f: BinaryIO) -> tuple[int, Dimensions, float]:
    """
    Parse binary STL file.
    
    Returns:
        (triangle_count, dimensions, volume)
    """
    # Skip header (80 bytes)
    f.seek(80)
    
    # Read triangle count
    count_data = f.read(4)
    if len(count_data) < 4:
        raise ValueError("Invalid STL: could not read triangle count")
    triangle_count = struct.unpack('<I', count_data)[0]
    
    # Initialize bounds
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')
    total_volume = 0.0
    
    # Read triangles
    for _ in range(triangle_count):
        # Each triangle: normal (3 floats) + 3 vertices (9 floats) + attribute (2 bytes)
        # Total: 50 bytes
        data = f.read(50)
        if len(data) < 50:
            break
        
        # Unpack: skip normal (first 3 floats), read 3 vertices
        values = struct.unpack('<12fH', data)
        
        # Extract vertices (skip normal which is values[0:3])
        v1 = values[3:6]
        v2 = values[6:9]
        v3 = values[9:12]
        
        # Update bounds
        for v in (v1, v2, v3):
            min_x = min(min_x, v[0])
            max_x = max(max_x, v[0])
            min_y = min(min_y, v[1])
            max_y = max(max_y, v[1])
            min_z = min(min_z, v[2])
            max_z = max(max_z, v[2])
        
        # Calculate signed volume contribution (for volume estimation)
        # Using signed volume of tetrahedron method
        total_volume += _signed_triangle_volume(v1, v2, v3)
    
    dimensions = Dimensions(min_x, max_x, min_y, max_y, min_z, max_z)
    volume = abs(total_volume)
    
    return triangle_count, dimensions, volume


def _read_ascii_stl(f: BinaryIO) -> tuple[int, Dimensions, float]:
    """
    Parse ASCII STL file.
    
    Returns:
        (triangle_count, dimensions, volume)
    """
    f.seek(0)
    content = f.read().decode('utf-8', errors='ignore')
    
    # Initialize
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')
    total_volume = 0.0
    triangle_count = 0
    current_vertices = []
    
    for line in content.split('\n'):
        line = line.strip().lower()
        if line.startswith('vertex'):
            parts = line.split()
            if len(parts) >= 4:
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                current_vertices.append((x, y, z))
                
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
                min_z = min(min_z, z)
                max_z = max(max_z, z)
                
                if len(current_vertices) == 3:
                    total_volume += _signed_triangle_volume(*current_vertices)
                    current_vertices = []
                    triangle_count += 1
    
    dimensions = Dimensions(min_x, max_x, min_y, max_y, min_z, max_z)
    volume = abs(total_volume)
    
    return triangle_count, dimensions, volume


def _signed_triangle_volume(v1: tuple, v2: tuple, v3: tuple) -> float:
    """Calculate signed volume of tetrahedron formed by triangle and origin."""
    # Cross product of v2-v1 and v3-v1
    ax, ay, az = v1
    bx, by, bz = v2
    cx, cy, cz = v3
    
    return (
        ax * (by * cz - bz * cy) +
        ay * (bz * cx - bx * cz) +
        az * (bx * cy - by * cx)
    ) / 6.0


def _is_binary_stl(f: BinaryIO) -> bool:
    """Check if STL file is binary or ASCII."""
    f.seek(0)
    header = f.read(80)
    
    # Check if starts with "solid" (ASCII indicator)
    if header.startswith(b'solid'):
        # Read more to confirm - binary files sometimes have "solid" in header
        f.seek(0)
        content = f.read(1000)
        # ASCII files have "facet normal" text
        if b'facet normal' in content.lower():
            return False
    
    return True


def analyze_stl(path: Path | str) -> MeshInfo:
    """
    Analyze an STL file without heavy dependencies.
    
    Args:
        path: Path to STL file
        
    Returns:
        MeshInfo with basic mesh statistics
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    file_size = path.stat().st_size
    
    with open(path, 'rb') as f:
        is_binary = _is_binary_stl(f)
        
        if is_binary:
            triangle_count, dimensions, volume = _read_binary_stl(f)
        else:
            triangle_count, dimensions, volume = _read_ascii_stl(f)
    
    return MeshInfo(
        path=path,
        format="stl",
        triangle_count=triangle_count,
        dimensions=dimensions,
        estimated_volume_mm3=volume,
        file_size_bytes=file_size,
        is_binary=is_binary,
    )


def validate_mesh(path: Path | str) -> ValidationResult:
    """
    Validate a mesh file for 3D printing.
    
    Performs basic checks without heavy dependencies.
    For full validation, use trimesh integration.
    
    Args:
        path: Path to mesh file
        
    Returns:
        ValidationResult with issues and warnings
    """
    path = Path(path)
    issues = []
    warnings = []
    info = None
    
    # Check file exists
    if not path.exists():
        issues.append(f"File not found: {path}")
        return ValidationResult(False, issues, warnings, None)
    
    # Check file size
    file_size = path.stat().st_size
    if file_size == 0:
        issues.append("File is empty")
        return ValidationResult(False, issues, warnings, None)
    
    if file_size < 84:  # Minimum valid binary STL
        issues.append("File too small to be valid STL")
        return ValidationResult(False, issues, warnings, None)
    
    # Check extension
    suffix = path.suffix.lower()
    if suffix not in ['.stl', '.obj', '.fbx', '.glb', '.gltf']:
        warnings.append(f"Unusual file extension: {suffix}")
    
    # Analyze STL
    if suffix == '.stl':
        try:
            info = analyze_stl(path)
            
            # Check triangle count
            if info.triangle_count == 0:
                issues.append("Mesh has no triangles")
            elif info.triangle_count < 4:
                warnings.append(f"Very low triangle count: {info.triangle_count}")
            
            # Check dimensions
            if info.dimensions:
                dims = info.dimensions
                if dims.max_dimension < 0.1:
                    warnings.append("Model is very small (< 0.1 units)")
                if dims.max_dimension > 10000:
                    warnings.append("Model is very large (> 10000 units)")
                
                # Check for flat model
                if dims.width < 0.001 or dims.depth < 0.001 or dims.height < 0.001:
                    warnings.append("Model appears to be flat in one dimension")
            
            # Check volume
            if info.estimated_volume_mm3 is not None:
                if info.estimated_volume_mm3 < 1:
                    warnings.append("Estimated volume is very small")
                    
        except Exception as e:
            issues.append(f"Failed to parse STL: {e}")
    else:
        # Can't fully analyze non-STL without trimesh
        warnings.append(f"Limited validation for {suffix} format")
        info = MeshInfo(
            path=path,
            format=suffix[1:],
            triangle_count=0,
            dimensions=None,
            estimated_volume_mm3=None,
            file_size_bytes=file_size,
        )
    
    is_valid = len(issues) == 0
    return ValidationResult(is_valid, issues, warnings, info)


def get_dimensions(path: Path | str) -> Dimensions:
    """
    Get dimensions of a mesh file.
    
    Args:
        path: Path to mesh file
        
    Returns:
        Dimensions object
    """
    info = analyze_stl(path)
    if info.dimensions is None:
        raise ValueError("Could not determine dimensions")
    return info.dimensions


def estimate_print_size(
    path: Path | str,
    target_height_mm: float,
) -> dict:
    """
    Estimate print size when scaled to target height.
    
    Args:
        path: Path to mesh file
        target_height_mm: Desired height in millimeters
        
    Returns:
        Dict with scaled dimensions and volume
    """
    info = analyze_stl(path)
    if info.dimensions is None:
        raise ValueError("Could not determine dimensions")
    
    dims = info.dimensions
    scale = dims.scale_factor(target_height_mm)
    
    return {
        "original": dims.to_dict(),
        "scale_factor": scale,
        "scaled": {
            "width_mm": dims.width * scale,
            "depth_mm": dims.depth * scale,
            "height_mm": dims.height * scale,
        },
        "estimated_volume_mm3": (info.estimated_volume_mm3 or 0) * (scale ** 3),
    }


# Optional trimesh integration
def repair_mesh_trimesh(path: Path | str, output_path: Path | str = None) -> Path:
    """
    Repair mesh using trimesh (if available).
    
    Fixes common issues:
    - Fills holes
    - Fixes normals
    - Removes degenerate faces
    
    Args:
        path: Input mesh path
        output_path: Output path (defaults to _repaired suffix)
        
    Returns:
        Path to repaired mesh
    """
    try:
        import trimesh
    except ImportError:
        raise ImportError(
            "trimesh not installed. Install with: pip install trimesh numpy"
        )
    
    path = Path(path)
    if output_path is None:
        output_path = path.with_stem(f"{path.stem}_repaired")
    output_path = Path(output_path)
    
    # Load mesh
    mesh = trimesh.load(path)
    
    # Repair operations
    if hasattr(mesh, 'fill_holes'):
        mesh.fill_holes()
    if hasattr(mesh, 'fix_normals'):
        mesh.fix_normals()
    if hasattr(mesh, 'remove_degenerate_faces'):
        mesh.remove_degenerate_faces()
    
    # Process to ensure watertight
    mesh = mesh.process(validate=True)
    
    # Export
    mesh.export(output_path)
    
    return output_path


def scale_mesh_trimesh(
    path: Path | str,
    target_height_mm: float,
    output_path: Path | str = None,
) -> Path:
    """
    Scale mesh to target height using trimesh (if available).
    
    Args:
        path: Input mesh path
        target_height_mm: Target height in mm
        output_path: Output path (defaults to _scaled suffix)
        
    Returns:
        Path to scaled mesh
    """
    try:
        import trimesh
    except ImportError:
        raise ImportError(
            "trimesh not installed. Install with: pip install trimesh numpy"
        )
    
    path = Path(path)
    if output_path is None:
        output_path = path.with_stem(f"{path.stem}_scaled")
    output_path = Path(output_path)
    
    # Load mesh
    mesh = trimesh.load(path)
    
    # Get current bounds
    bounds = mesh.bounds
    current_height = bounds[1][2] - bounds[0][2]
    
    if current_height > 0:
        scale_factor = target_height_mm / current_height
        mesh.apply_scale(scale_factor)
    
    # Export
    mesh.export(output_path)
    
    return output_path


__all__ = [
    # Data classes
    "Dimensions",
    "MeshInfo",
    "ValidationResult",
    # Core functions
    "analyze_stl",
    "validate_mesh",
    "get_dimensions",
    "estimate_print_size",
    # Trimesh functions (optional)
    "repair_mesh_trimesh",
    "scale_mesh_trimesh",
]
