"""
print3d - Automated 2D → 3D → Print Pipeline

A modular pipeline for generating 2D images, converting them to 3D models,
and sending them to 3D printing services.

Example:
    >>> from print3d import Pipeline
    >>> pipeline = Pipeline.from_env()
    >>> result = pipeline.run("a cute robot figurine")
    >>> print(result.mesh_path)
"""

__version__ = "0.1.0"
__author__ = "R2"

from .config import Config, get_config, load_config

# Lazy imports for optional modules
def __getattr__(name: str):
    if name == "ImageGenerator":
        from .image_gen import ImageGenerator
        return ImageGenerator
    elif name == "MeshGenerator":
        from .mesh_gen import MeshGenerator
        return MeshGenerator
    elif name == "PrintService":
        from .print_api import PrintService
        return PrintService
    elif name == "Pipeline":
        from .pipeline import Pipeline
        return Pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Config
    "Config",
    "get_config", 
    "load_config",
    # Modules (lazy loaded)
    "ImageGenerator",
    "MeshGenerator",
    "PrintService",
    "Pipeline",
    # Version
    "__version__",
]
