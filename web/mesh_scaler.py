"""
Mesh scaling utilities for custom dimensions.

Scales GLB/STL meshes to specific heights for 3D printing.
Uses trimesh when available, falls back to pure Python for GLB.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ScaleResult:
    """Result of mesh scaling operation."""
    input_path: Path
    output_path: Path
    original_height_mm: float
    target_height_mm: float
    scale_factor: float
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "input_path": str(self.input_path),
            "output_path": str(self.output_path),
            "original_height_mm": self.original_height_mm,
            "target_height_mm": self.target_height_mm,
            "scale_factor": self.scale_factor,
            "success": self.success,
            "error": self.error,
        }


def get_glb_bounds(glb_path: Path) -> Tuple[float, float, float, float, float, float]:
    """
    Extract bounding box from GLB file.

    Returns:
        (min_x, max_x, min_y, max_y, min_z, max_z)
    """
    with open(glb_path, 'rb') as f:
        # Read GLB header
        magic = f.read(4)
        if magic != b'glTF':
            raise ValueError("Not a valid GLB file")

        version = struct.unpack('<I', f.read(4))[0]
        length = struct.unpack('<I', f.read(4))[0]

        # Read JSON chunk
        chunk_length = struct.unpack('<I', f.read(4))[0]
        chunk_type = struct.unpack('<I', f.read(4))[0]

        if chunk_type != 0x4E4F534A:  # "JSON"
            raise ValueError("Expected JSON chunk")

        json_data = f.read(chunk_length).decode('utf-8')
        gltf = json.loads(json_data)

        # Find accessor bounds from meshes
        min_bounds = [float('inf'), float('inf'), float('inf')]
        max_bounds = [float('-inf'), float('-inf'), float('-inf')]

        accessors = gltf.get('accessors', [])
        for accessor in accessors:
            if 'min' in accessor and 'max' in accessor:
                for i in range(min(3, len(accessor['min']))):
                    min_bounds[i] = min(min_bounds[i], accessor['min'][i])
                    max_bounds[i] = max(max_bounds[i], accessor['max'][i])

        if min_bounds[0] == float('inf'):
            raise ValueError("Could not determine mesh bounds")

        return (
            min_bounds[0], max_bounds[0],
            min_bounds[1], max_bounds[1],
            min_bounds[2], max_bounds[2]
        )


def get_glb_height(glb_path: Path) -> float:
    """
    Get the height (Z dimension) of a GLB model.

    Assumes the model is in standard orientation with Z as up.
    Units are assumed to be meters (glTF standard).

    Returns:
        Height in millimeters
    """
    bounds = get_glb_bounds(glb_path)
    # GLB units are typically meters, convert to mm
    height_meters = bounds[5] - bounds[4]  # max_z - min_z
    return height_meters * 1000  # Convert to mm


def scale_glb_trimesh(
    input_path: Path,
    target_height_mm: float,
    output_path: Optional[Path] = None,
) -> ScaleResult:
    """
    Scale GLB using trimesh (recommended method).

    Args:
        input_path: Path to input GLB file
        target_height_mm: Desired height in millimeters
        output_path: Output path (defaults to input_scaled.glb)

    Returns:
        ScaleResult with operation details
    """
    try:
        import trimesh
    except ImportError:
        return ScaleResult(
            input_path=input_path,
            output_path=output_path or input_path,
            original_height_mm=0,
            target_height_mm=target_height_mm,
            scale_factor=1.0,
            success=False,
            error="trimesh not installed"
        )

    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.with_stem(f"{input_path.stem}_scaled")
    output_path = Path(output_path)

    try:
        # Load the GLB (can be a scene with multiple meshes)
        scene = trimesh.load(input_path)

        # Get bounds
        if hasattr(scene, 'bounds'):
            bounds = scene.bounds
        elif hasattr(scene, 'bounding_box'):
            bounds = scene.bounding_box.bounds
        else:
            # Single mesh
            bounds = scene.bounds

        # Calculate current height (assuming Z-up)
        current_height = bounds[1][2] - bounds[0][2]

        # GLB is typically in meters, but Meshy outputs might vary
        # We'll detect the scale based on reasonable model size
        if current_height < 0.001:  # Less than 1mm, probably already in meters
            current_height_mm = current_height * 1000
        elif current_height < 1:  # Less than 1m, assume meters
            current_height_mm = current_height * 1000
        else:  # Assume already in mm
            current_height_mm = current_height

        if current_height_mm <= 0:
            return ScaleResult(
                input_path=input_path,
                output_path=output_path,
                original_height_mm=0,
                target_height_mm=target_height_mm,
                scale_factor=1.0,
                success=False,
                error="Model has zero height"
            )

        # Calculate scale factor
        scale_factor = target_height_mm / current_height_mm

        # Apply uniform scaling
        if hasattr(scene, 'apply_scale'):
            scene.apply_scale(scale_factor)
        elif hasattr(scene, 'geometry'):
            # Scene with multiple geometries
            for geom in scene.geometry.values():
                if hasattr(geom, 'apply_scale'):
                    geom.apply_scale(scale_factor)

        # Export
        scene.export(output_path)

        return ScaleResult(
            input_path=input_path,
            output_path=output_path,
            original_height_mm=current_height_mm,
            target_height_mm=target_height_mm,
            scale_factor=scale_factor,
            success=True,
        )

    except Exception as e:
        return ScaleResult(
            input_path=input_path,
            output_path=output_path,
            original_height_mm=0,
            target_height_mm=target_height_mm,
            scale_factor=1.0,
            success=False,
            error=str(e)
        )


def scale_mesh(
    input_path: Path,
    target_height_mm: float,
    output_path: Optional[Path] = None,
) -> ScaleResult:
    """
    Scale a mesh to target height.

    Automatically detects format and uses appropriate method.

    Args:
        input_path: Path to mesh file (GLB, STL, OBJ)
        target_height_mm: Desired height in millimeters
        output_path: Output path (optional)

    Returns:
        ScaleResult with scaled mesh path
    """
    input_path = Path(input_path)

    if not input_path.exists():
        return ScaleResult(
            input_path=input_path,
            output_path=output_path or input_path,
            original_height_mm=0,
            target_height_mm=target_height_mm,
            scale_factor=1.0,
            success=False,
            error=f"File not found: {input_path}"
        )

    # Use trimesh for all formats (most reliable)
    return scale_glb_trimesh(input_path, target_height_mm, output_path)


def calculate_price_for_height(
    height_mm: float,
    base_price_cents: int = 5500,  # LATAM mini price
    base_height_mm: float = 50,
    exponent: float = 2.0,  # Volume scales with cube, but we use square for UX
) -> int:
    """
    Calculate price for a custom height.

    Uses a power-law scaling based on the assumption that
    material cost scales roughly with volume (height^3),
    but we use a gentler exponent for better UX.

    Args:
        height_mm: Desired height in millimeters
        base_price_cents: Price in cents for base height
        base_height_mm: Height corresponding to base price
        exponent: Scaling exponent (2.0 = quadratic)

    Returns:
        Price in cents (rounded to nearest 100 cents / $1)
    """
    if height_mm <= 0:
        return base_price_cents

    # Scale factor relative to base
    scale = height_mm / base_height_mm

    # Apply power-law scaling
    price = base_price_cents * (scale ** exponent)

    # Round to nearest dollar
    price_rounded = round(price / 100) * 100

    # Minimum price
    return max(price_rounded, base_price_cents)


def get_preset_or_custom_price(
    size_key: str,
    custom_height_mm: Optional[float],
    region: str = "latam",
) -> Tuple[float, int]:
    """
    Get height and price for preset or custom size.

    Args:
        size_key: Preset size key (mini, small, medium, large) or "custom"
        custom_height_mm: Height for custom size (required if size_key is "custom")
        region: Pricing region (latam or usa)

    Returns:
        (height_mm, price_cents)
    """
    # Import regional pricing
    try:
        from regional_pricing import SIZES, PRICES, get_region_for_country
    except ImportError:
        from web.regional_pricing import SIZES, PRICES, get_region_for_country

    # Handle preset sizes
    if size_key != "custom" and size_key in SIZES:
        size = SIZES[size_key]
        price = PRICES.get(region, PRICES["latam"]).get(size_key, 5500)
        return (size.height_mm, price)

    # Handle custom size
    if custom_height_mm is None or custom_height_mm <= 0:
        raise ValueError("custom_height_mm required for custom size")

    # Constrain to reasonable range
    height = max(30, min(300, custom_height_mm))  # 30mm - 300mm

    # Calculate price
    base_price = PRICES.get(region, PRICES["latam"]).get("mini", 5500)
    base_height = SIZES["mini"].height_mm

    price = calculate_price_for_height(
        height_mm=height,
        base_price_cents=base_price,
        base_height_mm=base_height,
    )

    return (height, price)


__all__ = [
    "ScaleResult",
    "scale_mesh",
    "scale_glb_trimesh",
    "get_glb_height",
    "get_glb_bounds",
    "calculate_price_for_height",
    "get_preset_or_custom_price",
]
