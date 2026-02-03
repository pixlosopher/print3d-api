"""
Pricing calculation for 3D prints.

Combines size and material to calculate final price.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Tuple

try:
    from .sizes import Size, get_size, get_all_sizes
    from .materials import Material, Color, get_material, get_color_for_material, get_all_materials
except ImportError:
    from sizes import Size, get_size, get_all_sizes
    from materials import Material, Color, get_material, get_color_for_material, get_all_materials


@dataclass
class PriceBreakdown:
    """Detailed price breakdown."""
    size_key: str
    material_key: str
    color_key: Optional[str]

    base_price_cents: int      # Material base price
    size_multiplier: float     # Size adjustment
    material_multiplier: float # Material complexity
    subtotal_cents: int        # Before any fees
    total_cents: int           # Final price

    size: Size
    material: Material
    color: Optional[Color]

    def to_dict(self) -> dict:
        return {
            "size_key": self.size_key,
            "material_key": self.material_key,
            "color_key": self.color_key,
            "base_price_cents": self.base_price_cents,
            "size_multiplier": self.size_multiplier,
            "material_multiplier": self.material_multiplier,
            "subtotal_cents": self.subtotal_cents,
            "total_cents": self.total_cents,
            "total_display": f"${self.total_cents / 100:.2f}",
            "currency": "USD",
            "size": self.size.to_dict(),
            "material": self.material.to_dict(),
            "color": self.color.to_dict() if self.color else None,
        }


def calculate_price(
    material_key: str,
    size_key: str,
    color_key: Optional[str] = None,
) -> PriceBreakdown:
    """
    Calculate the price for a specific configuration.

    Args:
        material_key: Key from MATERIALS
        size_key: Key from SIZES
        color_key: Optional color key (if material supports colors)

    Returns:
        PriceBreakdown with all price details

    Raises:
        ValueError: If material or size not found
    """
    material = get_material(material_key)
    if not material:
        raise ValueError(f"Unknown material: {material_key}")

    size = get_size(size_key)
    if not size:
        raise ValueError(f"Unknown size: {size_key}")

    # Get color if specified
    color = None
    if color_key and material.colors:
        color = get_color_for_material(material_key, color_key)

    # Calculate price
    # Formula: base_price * size_multiplier * material_multiplier
    base = material.base_price_cents
    size_mult = size.price_multiplier
    mat_mult = material.price_multiplier

    subtotal = int(base * size_mult * mat_mult)

    # Round to nearest dollar for cleaner prices
    total = round(subtotal / 100) * 100

    return PriceBreakdown(
        size_key=size_key,
        material_key=material_key,
        color_key=color_key,
        base_price_cents=base,
        size_multiplier=size_mult,
        material_multiplier=mat_mult,
        subtotal_cents=subtotal,
        total_cents=total,
        size=size,
        material=material,
        color=color,
    )


def get_price_matrix() -> List[dict]:
    """
    Generate a price matrix for all size/material combinations.

    Useful for displaying a pricing table in the UI.
    """
    matrix = []

    for material in get_all_materials():
        material_row = {
            "material": material.to_dict(),
            "prices": {},
        }

        for size in get_all_sizes():
            breakdown = calculate_price(material.key, size.key)
            material_row["prices"][size.key] = {
                "cents": breakdown.total_cents,
                "display": f"${breakdown.total_cents / 100:.0f}",
            }

        matrix.append(material_row)

    return matrix


def validate_order_config(
    material_key: str,
    size_key: str,
    color_key: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validate that an order configuration is valid.

    Returns:
        (is_valid, error_message)
    """
    material = get_material(material_key)
    if not material:
        return False, f"Invalid material: {material_key}"

    size = get_size(size_key)
    if not size:
        return False, f"Invalid size: {size_key}"

    # Check if color is required but missing
    if material.colors and not color_key:
        # Color is required for this material
        return False, f"Color required for material: {material_key}"

    # Check if color is valid for material
    if color_key:
        if not material.colors:
            return False, f"Material {material_key} does not support color selection"

        color = get_color_for_material(material_key, color_key)
        if not color:
            valid_colors = [c.key for c in material.colors]
            return False, f"Invalid color {color_key}. Valid: {valid_colors}"

    return True, None


__all__ = [
    "PriceBreakdown",
    "calculate_price",
    "get_price_matrix",
    "validate_order_config",
]
