"""
Pipeline orchestrator for print3d.

Combines all modules into a single, cohesive workflow:
2D Image → 3D Model → Print Service

Supports checkpointing, progress callbacks, and partial runs.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Literal

from .config import Config, get_config
from .image_gen import ImageGenerator, ImageResult, ImageStyle
from .mesh_gen import MeshGenerator, MeshResult, MeshOptions
from .mesh_utils import validate_mesh, estimate_print_size, ValidationResult
from .print_api import PrintService, ModelUpload, PricingResult, Material


class PipelineStage(str, Enum):
    """Pipeline execution stages."""
    INIT = "init"
    IMAGE_GENERATION = "image_generation"
    MESH_CONVERSION = "mesh_conversion"
    MESH_VALIDATION = "mesh_validation"
    PRINT_UPLOAD = "print_upload"
    PRICING = "pricing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class PipelineResult:
    """Complete result from pipeline execution."""
    # Input
    prompt: str
    style: ImageStyle
    size_mm: float
    
    # Stage results
    image: ImageResult | None = None
    mesh: MeshResult | None = None
    validation: ValidationResult | None = None
    upload: ModelUpload | None = None
    pricing: PricingResult | None = None
    
    # Status
    stage: PipelineStage = PipelineStage.INIT
    error: str | None = None
    
    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    
    # Paths
    image_path: Path | None = None
    mesh_path: Path | None = None
    
    @property
    def is_complete(self) -> bool:
        return self.stage == PipelineStage.COMPLETE
    
    @property
    def is_failed(self) -> bool:
        return self.stage == PipelineStage.FAILED
    
    @property
    def cheapest_material(self) -> Material | None:
        return self.pricing.cheapest if self.pricing else None
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "prompt": self.prompt,
            "style": self.style.value,
            "size_mm": self.size_mm,
            "stage": self.stage.value,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "image_path": str(self.image_path) if self.image_path else None,
            "mesh_path": str(self.mesh_path) if self.mesh_path else None,
            "image": self.image.to_dict() if self.image else None,
            "mesh": self.mesh.to_dict() if self.mesh else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "upload": self.upload.to_dict() if self.upload else None,
            "pricing": self.pricing.to_dict() if self.pricing else None,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, path: Path | str):
        """Save result to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())


# Progress callback type
ProgressCallback = Callable[[PipelineStage, float, str], None]


class Pipeline:
    """
    Full 2D → 3D → Print pipeline.
    
    Example:
        >>> pipeline = Pipeline.from_env()
        >>> result = pipeline.run("a cute robot", size_mm=50)
        >>> print(f"Model: {result.mesh_path}")
        >>> print(f"Cheapest: ${result.cheapest_material.price}")
    """
    
    def __init__(
        self,
        config: Config | None = None,
        output_dir: Path | str | None = None,
    ):
        self.config = config or get_config()
        self.output_dir = Path(output_dir) if output_dir else self.config.output_dir
        
        # Lazy-initialized modules
        self._image_gen: ImageGenerator | None = None
        self._mesh_gen: MeshGenerator | None = None
        self._print_service: PrintService | None = None
    
    @classmethod
    def from_env(cls, output_dir: Path | str | None = None) -> Pipeline:
        """Create pipeline from environment configuration."""
        return cls(get_config(), output_dir)
    
    @property
    def image_gen(self) -> ImageGenerator:
        if self._image_gen is None:
            self._image_gen = ImageGenerator(self.config)
        return self._image_gen
    
    @property
    def mesh_gen(self) -> MeshGenerator:
        if self._mesh_gen is None:
            self._mesh_gen = MeshGenerator(self.config)
        return self._mesh_gen
    
    @property
    def print_service(self) -> PrintService:
        if self._print_service is None:
            self._print_service = PrintService(self.config)
        return self._print_service
    
    def _ensure_output_dir(self) -> Path:
        """Create output directory if needed."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir
    
    async def run_async(
        self,
        prompt: str,
        style: ImageStyle = ImageStyle.FIGURINE,
        size_mm: float = 50.0,
        skip_print_upload: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> PipelineResult:
        """
        Run the full pipeline asynchronously.
        
        Args:
            prompt: Description of what to create
            style: Image style for 3D optimization
            size_mm: Target height in millimeters
            skip_print_upload: Skip uploading to print service
            on_progress: Callback(stage, progress, message)
            
        Returns:
            PipelineResult with all outputs
        """
        start_time = time.time()
        result = PipelineResult(
            prompt=prompt,
            style=style,
            size_mm=size_mm,
        )
        
        def report(stage: PipelineStage, progress: float, message: str):
            result.stage = stage
            if on_progress:
                on_progress(stage, progress, message)
        
        try:
            output_dir = self._ensure_output_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"print3d_{timestamp}"
            
            # Stage 1: Generate Image
            report(PipelineStage.IMAGE_GENERATION, 0.1, "Generating 2D image...")
            
            image_path = output_dir / f"{base_name}.png"
            result.image = await self.image_gen.generate_async(
                prompt=prompt,
                style=style,
                save_to=image_path,
            )
            result.image_path = result.image.local_path
            
            report(PipelineStage.IMAGE_GENERATION, 0.2, "Image generated")
            
            # Stage 2: Convert to 3D
            report(PipelineStage.MESH_CONVERSION, 0.3, "Converting to 3D model...")
            
            def mesh_progress(p: int):
                report(PipelineStage.MESH_CONVERSION, 0.3 + (p / 100) * 0.3, f"3D conversion: {p}%")
            
            result.mesh = await self.mesh_gen.from_image_async(
                image_url=result.image.url,
                output_dir=output_dir,
                format=self.config.default_mesh_format,
                on_progress=mesh_progress,
            )
            result.mesh_path = result.mesh.local_path
            
            report(PipelineStage.MESH_CONVERSION, 0.6, "3D model generated")
            
            # Stage 3: Validate Mesh
            report(PipelineStage.MESH_VALIDATION, 0.65, "Validating mesh...")
            
            if result.mesh_path:
                result.validation = validate_mesh(result.mesh_path)
                
                if not result.validation.is_valid:
                    report(PipelineStage.MESH_VALIDATION, 0.7, 
                           f"Validation issues: {result.validation.issues}")
            
            report(PipelineStage.MESH_VALIDATION, 0.7, "Mesh validated")
            
            # Stage 4: Upload to Print Service (optional)
            if not skip_print_upload and self.config.has_shapeways and result.mesh_path:
                report(PipelineStage.PRINT_UPLOAD, 0.75, "Uploading to print service...")
                
                result.upload = await self.print_service.upload_async(result.mesh_path)
                
                report(PipelineStage.PRINT_UPLOAD, 0.85, "Model uploaded")
                
                # Stage 5: Get Pricing
                report(PipelineStage.PRICING, 0.9, "Getting pricing...")
                
                result.pricing = await self.print_service.get_pricing_async(result.upload.model_id)
                
                report(PipelineStage.PRICING, 0.95, 
                       f"Pricing received: {len(result.pricing.materials)} materials")
            
            # Complete
            result.stage = PipelineStage.COMPLETE
            result.completed_at = datetime.now()
            result.duration_seconds = time.time() - start_time
            
            report(PipelineStage.COMPLETE, 1.0, "Pipeline complete!")
            
        except Exception as e:
            result.stage = PipelineStage.FAILED
            result.error = str(e)
            result.completed_at = datetime.now()
            result.duration_seconds = time.time() - start_time
            
            report(PipelineStage.FAILED, 0, f"Error: {e}")
            raise
        
        return result
    
    def run(
        self,
        prompt: str,
        style: ImageStyle = ImageStyle.FIGURINE,
        size_mm: float = 50.0,
        skip_print_upload: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> PipelineResult:
        """
        Synchronous wrapper for run_async.
        """
        return asyncio.run(
            self.run_async(prompt, style, size_mm, skip_print_upload, on_progress)
        )
    
    async def run_from_image_async(
        self,
        image_url: str,
        size_mm: float = 50.0,
        skip_print_upload: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> PipelineResult:
        """
        Run pipeline starting from an existing image.
        
        Skips image generation stage.
        """
        start_time = time.time()
        result = PipelineResult(
            prompt="[from image]",
            style=ImageStyle.CUSTOM,
            size_mm=size_mm,
        )
        result.image = ImageResult(url=image_url)
        
        def report(stage: PipelineStage, progress: float, message: str):
            result.stage = stage
            if on_progress:
                on_progress(stage, progress, message)
        
        try:
            output_dir = self._ensure_output_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"print3d_{timestamp}"
            
            # Stage 2: Convert to 3D
            report(PipelineStage.MESH_CONVERSION, 0.2, "Converting to 3D model...")
            
            result.mesh = await self.mesh_gen.from_image_async(
                image_url=image_url,
                output_dir=output_dir,
                format=self.config.default_mesh_format,
            )
            result.mesh_path = result.mesh.local_path
            
            # Stage 3: Validate
            if result.mesh_path:
                result.validation = validate_mesh(result.mesh_path)
            
            # Stage 4-5: Upload and Price (optional)
            if not skip_print_upload and self.config.has_shapeways and result.mesh_path:
                result.upload = await self.print_service.upload_async(result.mesh_path)
                result.pricing = await self.print_service.get_pricing_async(result.upload.model_id)
            
            result.stage = PipelineStage.COMPLETE
            result.completed_at = datetime.now()
            result.duration_seconds = time.time() - start_time
            
        except Exception as e:
            result.stage = PipelineStage.FAILED
            result.error = str(e)
            raise
        
        return result
    
    def run_from_image(
        self,
        image_url: str,
        size_mm: float = 50.0,
        skip_print_upload: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> PipelineResult:
        """Synchronous wrapper for run_from_image_async."""
        return asyncio.run(
            self.run_from_image_async(image_url, size_mm, skip_print_upload, on_progress)
        )
    
    async def run_from_mesh_async(
        self,
        mesh_path: Path | str,
        skip_print_upload: bool = False,
    ) -> PipelineResult:
        """
        Run pipeline starting from an existing mesh.
        
        Only validates and uploads for printing.
        """
        mesh_path = Path(mesh_path)
        result = PipelineResult(
            prompt="[from mesh]",
            style=ImageStyle.CUSTOM,
            size_mm=0,
        )
        result.mesh_path = mesh_path
        
        try:
            # Validate
            result.validation = validate_mesh(mesh_path)
            
            # Upload and price
            if not skip_print_upload and self.config.has_shapeways:
                result.upload = await self.print_service.upload_async(mesh_path)
                result.pricing = await self.print_service.get_pricing_async(result.upload.model_id)
            
            result.stage = PipelineStage.COMPLETE
            
        except Exception as e:
            result.stage = PipelineStage.FAILED
            result.error = str(e)
            raise
        
        return result
    
    def run_from_mesh(
        self,
        mesh_path: Path | str,
        skip_print_upload: bool = False,
    ) -> PipelineResult:
        """Synchronous wrapper for run_from_mesh_async."""
        return asyncio.run(self.run_from_mesh_async(mesh_path, skip_print_upload))
    
    def check_config(self) -> dict:
        """
        Check which pipeline features are available.
        
        Returns dict with availability status.
        """
        return {
            "image_generation": self.config.has_image_gen,
            "mesh_conversion": self.config.has_meshy,
            "print_service": self.config.has_shapeways,
            "full_pipeline": all([
                self.config.has_image_gen,
                self.config.has_meshy,
            ]),
            "missing": self.config.validate_for_pipeline(),
        }


__all__ = [
    "Pipeline",
    "PipelineResult",
    "PipelineStage",
    "ProgressCallback",
]
