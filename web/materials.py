"""
Material configuration for 3D printing.

Defines available materials with Shapeways integration.
Materials and colors based on Shapeways API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Color:
    """A color option for a material."""
    key: str
    name: str
    name_es: str
    hex_code: str  # For UI display

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "name_es": self.name_es,
            "hex_code": self.hex_code,
        }


@dataclass
class Material:
    """A printable material option."""
    key: str
    name: str
    name_es: str
    description: str
    description_es: str
    base_price_cents: int  # Base price in USD cents for smallest size
    price_multiplier: float  # Material complexity multiplier
    shapeways_material_id: Optional[str]  # Shapeways API material ID
    colors: List[Color]  # Available colors (empty = no color choice)
    supports_full_color: bool  # Can print texture colors
    min_detail_mm: float  # Minimum detail size in mm
    finish: str  # Surface finish description

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "name_es": self.name_es,
            "description": self.description,
            "description_es": self.description_es,
            "base_price_cents": self.base_price_cents,
            "price_multiplier": self.price_multiplier,
            "colors": [c.to_dict() for c in self.colors] if self.colors else None,
            "supports_full_color": self.supports_full_color,
            "min_detail_mm": self.min_detail_mm,
            "finish": self.finish,
        }


# Common colors for plastic materials
PLASTIC_COLORS = [
    Color("white", "White", "Blanco", "#FFFFFF"),
    Color("black", "Black", "Negro", "#1A1A1A"),
    Color("red", "Red", "Rojo", "#E53935"),
    Color("blue", "Blue", "Azul", "#1E88E5"),
    Color("green", "Green", "Verde", "#43A047"),
    Color("yellow", "Yellow", "Amarillo", "#FDD835"),
    Color("orange", "Orange", "Naranja", "#FB8C00"),
    Color("pink", "Pink", "Rosa", "#EC407A"),
    Color("purple", "Purple", "Morado", "#8E24AA"),
]

RESIN_COLORS = [
    Color("white", "White", "Blanco", "#F5F5F5"),
    Color("black", "Black", "Negro", "#212121"),
    Color("clear", "Clear", "Transparente", "#E3F2FD"),
]

METAL_FINISHES = [
    Color("silver", "Polished Silver", "Plata Pulida", "#C0C0C0"),
    Color("bronze", "Antique Bronze", "Bronce Antiguo", "#CD7F32"),
]


# Available materials
# Note: shapeways_material_id values need to be fetched from Shapeways API
# These are placeholders - run fetch_shapeways_materials() to get real IDs
MATERIALS: Dict[str, Material] = {
    "plastic_white": Material(
        key="plastic_white",
        name="White Plastic",
        name_es="Plástico Blanco",
        description="Affordable, matte finish. Great for prototypes.",
        description_es="Económico, acabado mate. Ideal para prototipos.",
        base_price_cents=2900,  # $29
        price_multiplier=1.0,
        shapeways_material_id=None,  # Versatile Plastic - White
        colors=[],  # No color choice
        supports_full_color=False,
        min_detail_mm=0.8,
        finish="Matte",
    ),
    "plastic_color": Material(
        key="plastic_color",
        name="Colored Plastic",
        name_es="Plástico Color",
        description="Durable nylon in your favorite color.",
        description_es="Nylon duradero en tu color favorito.",
        base_price_cents=3900,  # $39
        price_multiplier=1.2,
        shapeways_material_id=None,  # Versatile Plastic - Colored
        colors=PLASTIC_COLORS,
        supports_full_color=False,
        min_detail_mm=0.8,
        finish="Matte",
    ),
    "resin_premium": Material(
        key="resin_premium",
        name="Premium Resin",
        name_es="Resina Premium",
        description="High detail, smooth surface. Museum quality.",
        description_es="Alto detalle, superficie lisa. Calidad museo.",
        base_price_cents=5900,  # $59
        price_multiplier=1.5,
        shapeways_material_id=None,  # High Definition Resin
        colors=RESIN_COLORS,
        supports_full_color=False,
        min_detail_mm=0.3,
        finish="Smooth",
    ),
    "full_color": Material(
        key="full_color",
        name="Full Color",
        name_es="Full Color",
        description="Prints the exact colors from your design. Vibrant and unique.",
        description_es="Imprime los colores exactos de tu diseño. Vibrante y único.",
        base_price_cents=7900,  # $79
        price_multiplier=2.0,
        shapeways_material_id=None,  # Full Color Nylon 12
        colors=[],  # Colors come from texture
        supports_full_color=True,
        min_detail_mm=0.5,
        finish="Matte with color",
    ),
    "metal_steel": Material(
        key="metal_steel",
        name="Stainless Steel",
        name_es="Acero Inoxidable",
        description="Real metal. Heavy, durable, impressive.",
        description_es="Metal real. Pesado, duradero, impresionante.",
        base_price_cents=14900,  # $149
        price_multiplier=3.0,
        shapeways_material_id=None,  # Stainless Steel
        colors=METAL_FINISHES,
        supports_full_color=False,
        min_detail_mm=1.0,
        finish="Polished metal",
    ),
}


def get_material(key: str) -> Optional[Material]:
    """Get material by key."""
    return MATERIALS.get(key)


def get_all_materials() -> List[Material]:
    """Get all materials ordered by price."""
    return sorted(MATERIALS.values(), key=lambda m: m.base_price_cents)


def get_materials_dict() -> dict:
    """Get all materials as dictionary for API response."""
    return {key: mat.to_dict() for key, mat in MATERIALS.items()}


def get_color_for_material(material_key: str, color_key: str) -> Optional[Color]:
    """Get a specific color for a material."""
    material = get_material(material_key)
    if not material or not material.colors:
        return None

    for color in material.colors:
        if color.key == color_key:
            return color
    return None


__all__ = [
    "Material",
    "Color",
    "MATERIALS",
    "PLASTIC_COLORS",
    "RESIN_COLORS",
    "METAL_FINISHES",
    "get_material",
    "get_all_materials",
    "get_materials_dict",
    "get_color_for_material",
]
