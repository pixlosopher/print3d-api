"""
Size configuration for 3D printed models.

Defines available sizes with pricing multipliers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, List


@dataclass(frozen=True)
class Size:
    """A printable size option."""
    key: str
    name: str
    name_es: str
    height_mm: int
    description: str
    description_es: str
    price_multiplier: float

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "name_es": self.name_es,
            "height_mm": self.height_mm,
            "height_cm": self.height_mm / 10,
            "description": self.description,
            "description_es": self.description_es,
            "price_multiplier": self.price_multiplier,
        }


# Available sizes
# Updated 2026-02 - aligned with regional_pricing.py
SIZES: Dict[str, Size] = {
    "mini": Size(
        key="mini",
        name="Mini",
        name_es="Mini",
        height_mm=50,
        description="Keychain, desk toy",
        description_es="Llavero, juguete de escritorio",
        price_multiplier=1.0,
    ),
    "small": Size(
        key="small",
        name="Small",
        name_es="Pequeño",
        height_mm=75,
        description="Desk figure, collectible",
        description_es="Figura de escritorio, coleccionable",
        price_multiplier=1.5,
    ),
    "medium": Size(
        key="medium",
        name="Medium",
        name_es="Mediano",
        height_mm=100,
        description="Display piece, gift",
        description_es="Pieza de exhibición, regalo",
        price_multiplier=2.4,
    ),
    "large": Size(
        key="large",
        name="Large",
        name_es="Grande",
        height_mm=150,
        description="Statement piece, premium gift",
        description_es="Pieza destacada, regalo premium",
        price_multiplier=3.6,
    ),
    "xl": Size(
        key="xl",
        name="XL",
        name_es="Extra Grande",
        height_mm=200,
        description="Exhibition piece, centerpiece",
        description_es="Pieza de exhibición, centro de mesa",
        price_multiplier=5.2,
    ),
}


def get_size(key: str) -> Optional[Size]:
    """Get size by key."""
    return SIZES.get(key)


def get_all_sizes() -> List[Size]:
    """Get all sizes ordered by height."""
    return sorted(SIZES.values(), key=lambda s: s.height_mm)


def get_sizes_dict() -> dict:
    """Get all sizes as dictionary for API response."""
    return {key: size.to_dict() for key, size in SIZES.items()}


__all__ = ["Size", "SIZES", "get_size", "get_all_sizes", "get_sizes_dict"]
