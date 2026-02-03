"""
Mesh generation options for Meshy API.

Defines available options that users can customize for their 3D model.
Based on Meshy API documentation: https://docs.meshy.ai/en/api/image-to-3d
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum


class MeshStyle(str, Enum):
    """Model style options."""
    STANDARD = "standard"  # High detail, realistic
    LOWPOLY = "lowpoly"    # Clean polygons, stylized


class AIModel(str, Enum):
    """Meshy AI model versions."""
    MESHY_5 = "meshy-5"
    MESHY_6 = "meshy-6"
    LATEST = "latest"  # Currently meshy-6


class SymmetryMode(str, Enum):
    """Symmetry enforcement options."""
    AUTO = "auto"  # AI decides
    ON = "on"      # Force symmetry
    OFF = "off"    # No symmetry


class Topology(str, Enum):
    """Mesh topology options."""
    QUAD = "quad"        # Better for editing
    TRIANGLE = "triangle"  # Better for printing


@dataclass
class MeshStyleOption:
    """A mesh style option for the UI."""
    key: str
    name: str
    name_es: str
    description: str
    description_es: str
    meshy_model_type: str  # "standard" or "lowpoly"
    recommended_polycount: int

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "name_es": self.name_es,
            "description": self.description,
            "description_es": self.description_es,
        }


# User-facing style options
MESH_STYLES: Dict[str, MeshStyleOption] = {
    "detailed": MeshStyleOption(
        key="detailed",
        name="Detailed",
        name_es="Detallado",
        description="High detail, realistic look. Best for organic shapes.",
        description_es="Alto detalle, aspecto realista. Mejor para formas orgánicas.",
        meshy_model_type="standard",
        recommended_polycount=100000,
    ),
    "stylized": MeshStyleOption(
        key="stylized",
        name="Stylized",
        name_es="Estilizado",
        description="Clean low-poly look. Modern and artistic.",
        description_es="Aspecto low-poly limpio. Moderno y artístico.",
        meshy_model_type="lowpoly",
        recommended_polycount=5000,
    ),
}


@dataclass
class MeshGenerationOptions:
    """
    Complete options for Meshy API call.

    These are the actual parameters sent to Meshy, derived from
    user selections and material requirements.
    """
    # Core options
    model_type: str = "standard"       # "standard" or "lowpoly"
    ai_model: str = "latest"           # "meshy-5", "meshy-6", "latest"
    topology: str = "triangle"         # "quad" or "triangle"
    target_polycount: Optional[int] = None  # 100-300,000

    # Texture options
    enable_pbr: bool = False           # Generate PBR maps (metallic, roughness, normal)
    should_texture: bool = True        # Generate textures

    # Geometry options
    symmetry_mode: str = "auto"        # "auto", "on", "off"

    def to_api_params(self) -> dict:
        """Convert to Meshy API parameters."""
        params = {
            "model_type": self.model_type,
            "ai_model": self.ai_model,
            "topology": self.topology,
            "symmetry_mode": self.symmetry_mode,
            "should_texture": self.should_texture,
        }

        if self.target_polycount:
            params["target_polycount"] = self.target_polycount

        if self.enable_pbr:
            params["enable_pbr"] = True

        return params

    @classmethod
    def from_user_selection(
        cls,
        style_key: str,
        material_key: str,
    ) -> "MeshGenerationOptions":
        """
        Create options from user's style and material selection.

        Args:
            style_key: "detailed" or "stylized"
            material_key: Material key from materials.py
        """
        try:
            from .materials import get_material
        except ImportError:
            from materials import get_material

        style = MESH_STYLES.get(style_key, MESH_STYLES["detailed"])
        material = get_material(material_key)

        # Determine if we need PBR textures
        # Full color material benefits from PBR for better color reproduction
        enable_pbr = material.supports_full_color if material else False

        return cls(
            model_type=style.meshy_model_type,
            ai_model="latest",
            topology="triangle",  # Always triangle for 3D printing
            target_polycount=style.recommended_polycount,
            enable_pbr=enable_pbr,
            should_texture=True,
            symmetry_mode="auto",
        )


def get_mesh_style(key: str) -> Optional[MeshStyleOption]:
    """Get mesh style by key."""
    return MESH_STYLES.get(key)


def get_all_mesh_styles() -> List[MeshStyleOption]:
    """Get all mesh styles."""
    return list(MESH_STYLES.values())


def get_mesh_styles_dict() -> dict:
    """Get all mesh styles as dictionary for API response."""
    return {key: style.to_dict() for key, style in MESH_STYLES.items()}


__all__ = [
    "MeshStyle",
    "AIModel",
    "SymmetryMode",
    "Topology",
    "MeshStyleOption",
    "MeshGenerationOptions",
    "MESH_STYLES",
    "get_mesh_style",
    "get_all_mesh_styles",
    "get_mesh_styles_dict",
]
