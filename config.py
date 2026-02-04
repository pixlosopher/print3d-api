"""
Configuration management for print3d pipeline.

Loads settings from environment variables or .env file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Pipeline configuration loaded from environment."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Meshy API (Image to 3D)
    meshy_api_key: str = Field(default="", description="Meshy API key for 3D generation")
    meshy_base_url: str = Field(default="https://api.meshy.ai", description="Meshy API base URL")
    
    # Shapeways API (3D Printing)
    shapeways_client_id: str = Field(default="", description="Shapeways OAuth client ID")
    shapeways_client_secret: str = Field(default="", description="Shapeways OAuth client secret")
    shapeways_base_url: str = Field(default="https://api.shapeways.com", description="Shapeways API base URL")
    
    # fal.ai (Image Generation)
    fal_key: str = Field(default="", description="fal.ai API key")
    fal_base_url: str = Field(default="https://fal.run", description="fal.ai API base URL")
    
    # Alternative: Direct Gemini
    gemini_api_key: str = Field(default="", description="Google Gemini API key (alternative to fal)")
    
    # Pipeline settings
    output_dir: Path = Field(default=Path("./output"), description="Output directory for generated files")
    default_mesh_format: Literal["stl", "obj", "fbx", "glb"] = Field(default="stl", description="Default 3D format")
    default_size_mm: float = Field(default=50.0, description="Default model height in mm")
    mesh_timeout_seconds: int = Field(default=600, description="Timeout for 3D generation (10 min)")

    # Payment (Stripe)
    stripe_secret_key: str = Field(default="", description="Stripe secret API key")
    stripe_webhook_secret: str = Field(default="", description="Stripe webhook signing secret")
    stripe_publishable_key: str = Field(default="", description="Stripe publishable key for frontend")

    # Payment (PayPal)
    paypal_client_id: str = Field(default="", description="PayPal client ID")
    paypal_client_secret: str = Field(default="", description="PayPal client secret")
    paypal_mode: Literal["sandbox", "live"] = Field(default="sandbox", description="PayPal mode")

    # Database
    database_url: str = Field(default="sqlite:///./print3d.db", description="Database connection URL")

    # Email (Resend)
    resend_api_key: str = Field(default="", description="Resend API key for transactional emails")
    from_email: str = Field(default="orders@print3d.com", description="From email address")

    # Frontend URL
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend URL for redirects")
    
    @field_validator("output_dir", mode="before")
    @classmethod
    def ensure_path(cls, v):
        return Path(v) if isinstance(v, str) else v
    
    def ensure_output_dir(self) -> Path:
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir
    
    @property
    def has_meshy(self) -> bool:
        """Check if Meshy API is configured."""
        return bool(self.meshy_api_key)
    
    @property
    def has_shapeways(self) -> bool:
        """Check if Shapeways API is configured."""
        return bool(self.shapeways_client_id and self.shapeways_client_secret)
    
    @property
    def has_image_gen(self) -> bool:
        """Check if any image generation is configured."""
        return bool(self.fal_key or self.gemini_api_key)

    @property
    def has_stripe(self) -> bool:
        """Check if Stripe is configured."""
        return bool(self.stripe_secret_key)

    @property
    def has_paypal(self) -> bool:
        """Check if PayPal is configured."""
        return bool(self.paypal_client_id and self.paypal_client_secret)

    @property
    def has_payments(self) -> bool:
        """Check if any payment provider is configured."""
        return self.has_stripe or self.has_paypal

    @property
    def has_email(self) -> bool:
        """Check if email is configured."""
        return bool(self.resend_api_key)

    def validate_for_pipeline(self) -> list[str]:
        """Validate configuration for full pipeline. Returns list of missing items."""
        missing = []
        if not self.has_image_gen:
            missing.append("Image generation (FAL_KEY or GEMINI_API_KEY)")
        if not self.has_meshy:
            missing.append("Meshy API (MESHY_API_KEY)")
        if not self.has_shapeways:
            missing.append("Shapeways API (SHAPEWAYS_CLIENT_ID, SHAPEWAYS_CLIENT_SECRET)")
        return missing


# Singleton instance
_config: Config | None = None


def get_config() -> Config:
    """Get or create the config singleton."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def load_config(env_file: str | Path | None = None) -> Config:
    """Load config from specific env file."""
    global _config
    if env_file:
        _config = Config(_env_file=env_file)
    else:
        _config = Config()
    return _config


# Convenience exports
__all__ = ["Config", "get_config", "load_config"]
