"""
Image generation module for print3d pipeline.

Uses Google Gemini (Imagen 3) as the primary backend.
Optimizes prompts for 3D-printable outputs.
"""

from __future__ import annotations

import asyncio
import base64
import httpx
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal

try:
    from .config import Config, get_config
except ImportError:
    from config import Config, get_config


class ImageStyle(str, Enum):
    """Predefined styles optimized for 3D conversion."""
    FIGURINE = "figurine"
    OBJECT = "object"
    CHARACTER = "character"
    SCULPTURE = "sculpture"
    MINIATURE = "miniature"
    CUSTOM = "custom"


# Prompt templates that work well for image-to-3D conversion
STYLE_TEMPLATES = {
    ImageStyle.FIGURINE: (
        "3D printable figurine of {subject}, "
        "front-facing view, T-pose if character, "
        "clean white background, studio lighting, "
        "high detail, centered composition, "
        "solid base for stability"
    ),
    ImageStyle.OBJECT: (
        "Product photograph of {subject}, "
        "white background, centered, "
        "isometric view, studio lighting, "
        "sharp details, no shadows, "
        "isolated object"
    ),
    ImageStyle.CHARACTER: (
        "3D character design of {subject}, "
        "full body, A-pose or T-pose, "
        "front view, white background, "
        "game-ready style, clear silhouette, "
        "suitable for 3D modeling"
    ),
    ImageStyle.SCULPTURE: (
        "Classical sculpture of {subject}, "
        "marble or bronze style, "
        "dramatic lighting, museum quality, "
        "detailed surface texture, "
        "isolated on dark background"
    ),
    ImageStyle.MINIATURE: (
        "Tabletop miniature of {subject}, "
        "28mm scale style, high detail, "
        "heroic proportions, dynamic pose, "
        "clean base, paintable surface detail"
    ),
}


@dataclass
class ImageResult:
    """Result from image generation."""
    url: str
    local_path: Path | None = None
    prompt: str = ""
    original_prompt: str = ""
    style: ImageStyle = ImageStyle.CUSTOM
    width: int = 1024
    height: int = 1024
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "url": self.url,
            "local_path": str(self.local_path) if self.local_path else None,
            "prompt": self.prompt,
            "original_prompt": self.original_prompt,
            "style": self.style.value,
            "width": self.width,
            "height": self.height,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class ImageGenerator:
    """
    Generate images optimized for 3D conversion.

    Uses Google Gemini 2.0 Flash as the primary backend.

    Example:
        >>> gen = ImageGenerator()
        >>> result = gen.generate("a cute robot", style=ImageStyle.FIGURINE)
        >>> print(result.url)
    """

    # Gemini API endpoints
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    # Use Gemini 2.0 Flash experimental with image generation
    GEMINI_MODEL = "gemini-2.0-flash-exp-image-generation"

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialized HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_prompt(self, subject: str, style: ImageStyle) -> str:
        """Build optimized prompt from subject and style."""
        if style == ImageStyle.CUSTOM:
            return subject

        template = STYLE_TEMPLATES.get(style, "{subject}")
        return template.format(subject=subject)

    async def generate_async(
        self,
        prompt: str,
        style: ImageStyle = ImageStyle.FIGURINE,
        size: Literal["square", "portrait", "landscape"] = "square",
        save_to: Path | None = None,
    ) -> ImageResult:
        """
        Generate an image asynchronously.

        Args:
            prompt: Description of what to generate
            style: Predefined style for 3D optimization
            size: Image aspect ratio
            save_to: Optional path to save the image

        Returns:
            ImageResult with URL and metadata
        """
        # Build optimized prompt
        full_prompt = self._build_prompt(prompt, style)

        # Use Gemini as primary, fal.ai as fallback
        if self.config.gemini_api_key:
            result = await self._generate_gemini(full_prompt, size, save_to)
        elif self.config.fal_key:
            result = await self._generate_fal(full_prompt, size)
        else:
            raise ValueError("No image generation API configured. Set GEMINI_API_KEY or FAL_KEY.")

        # Update result with prompt info
        result.original_prompt = prompt
        result.prompt = full_prompt
        result.style = style

        # Save locally if requested and not already saved
        if save_to and not result.local_path:
            result.local_path = await self._download_image(result.url, save_to)

        return result

    async def _generate_gemini(
        self,
        prompt: str,
        size: Literal["square", "portrait", "landscape"],
        save_to: Path | None = None,
    ) -> ImageResult:
        """Generate image using Google Gemini 2.0 Flash with image generation."""

        # Gemini 2.0 Flash generateContent endpoint
        url = f"{self.GEMINI_BASE_URL}/models/{self.GEMINI_MODEL}:generateContent"

        # Enhanced prompt for image generation
        enhanced_prompt = f"Generate an image: {prompt}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": enhanced_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            }
        }

        response = await self.client.post(
            url,
            headers={"Content-Type": "application/json"},
            params={"key": self.config.gemini_api_key},
            json=payload,
        )

        if response.status_code != 200:
            error_detail = response.text
            raise ValueError(f"Gemini API error ({response.status_code}): {error_detail}")

        data = response.json()

        # Extract image from response
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError(f"No candidates in Gemini response: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])

        # Find the image part
        image_b64 = None
        mime_type = "image/png"

        for part in parts:
            if "inlineData" in part:
                image_b64 = part["inlineData"].get("data")
                mime_type = part["inlineData"].get("mimeType", "image/png")
                break

        if not image_b64:
            # If no image, Gemini may have returned text explaining why
            text_response = ""
            for part in parts:
                if "text" in part:
                    text_response += part["text"]
            raise ValueError(f"No image data in Gemini response. Model said: {text_response}")

        # Determine dimensions based on aspect ratio
        dims = {"square": (1024, 1024), "portrait": (768, 1024), "landscape": (1024, 768)}
        width, height = dims[size]

        # Save the image directly if path provided
        if save_to:
            save_path = Path(save_to)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            image_bytes = base64.b64decode(image_b64)
            save_path.write_bytes(image_bytes)

            return ImageResult(
                url=str(save_path),  # Local file path as URL
                local_path=save_path,
                width=width,
                height=height,
                metadata={
                    "backend": "gemini",
                    "model": self.GEMINI_MODEL,
                },
            )

        # Return as data URL if no save path
        data_url = f"data:{mime_type};base64,{image_b64}"

        return ImageResult(
            url=data_url,
            width=width,
            height=height,
            metadata={
                "backend": "gemini",
                "model": self.GEMINI_MODEL,
                "is_base64": True,
            },
        )

    async def _generate_fal(
        self,
        prompt: str,
        size: Literal["square", "portrait", "landscape"],
    ) -> ImageResult:
        """Generate image using fal.ai (Flux) as fallback."""

        # Map size to dimensions
        size_map = {
            "square": {"width": 1024, "height": 1024},
            "portrait": {"width": 768, "height": 1024},
            "landscape": {"width": 1024, "height": 768},
        }
        dims = size_map[size]

        response = await self.client.post(
            f"{self.config.fal_base_url}/fal-ai/flux/dev",
            headers={
                "Authorization": f"Key {self.config.fal_key}",
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                "image_size": size,
                "num_images": 1,
                "enable_safety_checker": True,
            },
        )
        response.raise_for_status()
        data = response.json()

        # Extract image URL from response
        image_url = data.get("images", [{}])[0].get("url", "")
        if not image_url:
            raise ValueError(f"No image URL in response: {data}")

        return ImageResult(
            url=image_url,
            width=dims["width"],
            height=dims["height"],
            metadata={"backend": "fal", "model": "flux-dev", "raw_response": data},
        )

    async def _download_image(self, url: str, save_to: Path) -> Path:
        """Download image from URL to local path."""
        save_to = Path(save_to)
        save_to.parent.mkdir(parents=True, exist_ok=True)

        # Handle base64 data URLs
        if url.startswith("data:"):
            # Extract base64 data
            header, data = url.split(",", 1)
            image_bytes = base64.b64decode(data)
        else:
            # Download from URL
            response = await self.client.get(url)
            response.raise_for_status()
            image_bytes = response.content

        save_to.write_bytes(image_bytes)
        return save_to

    def generate(
        self,
        prompt: str,
        style: ImageStyle = ImageStyle.FIGURINE,
        size: Literal["square", "portrait", "landscape"] = "square",
        save_to: Path | None = None,
    ) -> ImageResult:
        """
        Synchronous wrapper for generate_async.

        Args:
            prompt: Description of what to generate
            style: Predefined style for 3D optimization
            size: Image aspect ratio
            save_to: Optional path to save the image

        Returns:
            ImageResult with URL and metadata
        """
        # Handle running in different contexts (main thread, worker thread, etc.)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're inside an async context or a thread with a running loop
            # Create a new loop in a thread-safe way
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.generate_async(prompt, style, size, save_to)
                )
                return future.result()
        else:
            # No loop running, safe to use asyncio.run
            # Create a fresh client for this call to avoid closed loop issues
            self._client = None
            return asyncio.run(self.generate_async(prompt, style, size, save_to))

    def generate_for_3d(
        self,
        subject: str,
        style: ImageStyle = ImageStyle.FIGURINE,
        save_to: Path | None = None,
    ) -> ImageResult:
        """
        Generate image optimized specifically for 3D conversion.

        Convenience method that uses best practices for image-to-3D.

        Args:
            subject: What to create (e.g., "a cute robot")
            style: Type of 3D model to create
            save_to: Optional path to save the image

        Returns:
            ImageResult optimized for Meshy/3D conversion
        """
        return self.generate(
            prompt=subject,
            style=style,
            size="square",  # Square works best for 3D
            save_to=save_to,
        )


# Convenience function
def generate_image(
    prompt: str,
    style: ImageStyle = ImageStyle.FIGURINE,
    save_to: Path | None = None,
) -> ImageResult:
    """
    Quick function to generate an image.

    Example:
        >>> from print3d.image_gen import generate_image, ImageStyle
        >>> result = generate_image("a robot", ImageStyle.FIGURINE)
    """
    gen = ImageGenerator()
    return gen.generate_for_3d(prompt, style, save_to)


__all__ = [
    "ImageGenerator",
    "ImageResult",
    "ImageStyle",
    "STYLE_TEMPLATES",
    "generate_image",
]
