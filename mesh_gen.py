"""
Mesh generation module for print3d pipeline.

Converts 2D images to 3D models using Meshy.ai API.
"""

from __future__ import annotations

import asyncio
import httpx
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal

try:
    from .config import Config, get_config
except ImportError:
    from config import Config, get_config


class MeshTopology(str, Enum):
    """Mesh topology options."""
    QUAD = "quad"      # Better for editing
    TRIANGLE = "triangle"  # Better for printing


class TaskStatus(str, Enum):
    """Meshy task status values."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


@dataclass
class MeshOptions:
    """Options for mesh generation."""
    topology: MeshTopology = MeshTopology.TRIANGLE
    target_polycount: int | None = None
    enable_pbr: bool = True  # Physically-based rendering textures
    
    def to_api_params(self) -> dict:
        """Convert to Meshy API parameters."""
        params = {
            "topology": self.topology.value,
            "enable_pbr": self.enable_pbr,
        }
        if self.target_polycount:
            params["target_polycount"] = self.target_polycount
        return params


@dataclass
class MeshResult:
    """Result from mesh generation."""
    task_id: str
    status: TaskStatus
    model_urls: dict[str, str] = field(default_factory=dict)  # format -> url
    thumbnail_url: str = ""
    texture_urls: list[str] = field(default_factory=list)
    local_path: Path | None = None
    progress: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    metadata: dict = field(default_factory=dict)
    
    @property
    def is_complete(self) -> bool:
        return self.status == TaskStatus.SUCCEEDED
    
    @property
    def is_failed(self) -> bool:
        return self.status in (TaskStatus.FAILED, TaskStatus.EXPIRED)
    
    @property
    def stl_url(self) -> str | None:
        return self.model_urls.get("stl")
    
    @property
    def obj_url(self) -> str | None:
        return self.model_urls.get("obj")
    
    @property
    def fbx_url(self) -> str | None:
        return self.model_urls.get("fbx")
    
    @property
    def glb_url(self) -> str | None:
        return self.model_urls.get("glb")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "model_urls": self.model_urls,
            "thumbnail_url": self.thumbnail_url,
            "texture_urls": self.texture_urls,
            "local_path": str(self.local_path) if self.local_path else None,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "metadata": self.metadata,
        }


class MeshyAPIError(Exception):
    """Error from Meshy API."""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class MeshGenerator:
    """
    Convert images to 3D models using Meshy.ai.
    
    Example:
        >>> gen = MeshGenerator()
        >>> result = gen.from_image("https://example.com/image.png")
        >>> print(result.stl_url)
    """
    
    API_VERSION = "openapi/v1"
    
    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self._client: httpx.AsyncClient | None = None
        
        if not self.config.has_meshy:
            raise ValueError("Meshy API key not configured. Set MESHY_API_KEY.")
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialized HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.meshy_base_url,
                headers={
                    "Authorization": f"Bearer {self.config.meshy_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def create_task(
        self,
        image_url: str,
        options: MeshOptions | None = None,
    ) -> str:
        """
        Create an image-to-3D task.
        
        Args:
            image_url: URL of the source image
            options: Mesh generation options
            
        Returns:
            Task ID for polling status
        """
        options = options or MeshOptions()
        
        payload = {
            "image_url": image_url,
            **options.to_api_params(),
        }
        
        response = await self.client.post(
            f"/{self.API_VERSION}/image-to-3d",
            json=payload,
        )

        # Meshy returns 200 or 202 for successful task creation
        if response.status_code not in (200, 202):
            raise MeshyAPIError(
                f"Failed to create task: {response.text}",
                status_code=response.status_code,
                response=response.json() if response.content else None,
            )

        data = response.json()
        # Task ID can be in 'result' or directly in response
        task_id = data.get("result") or data.get("id")
        if not task_id:
            raise MeshyAPIError(f"No task ID in response: {data}")
        return task_id
    
    async def get_task_status(self, task_id: str) -> MeshResult:
        """
        Get the status of a task.
        
        Args:
            task_id: The task ID to check
            
        Returns:
            MeshResult with current status and URLs if complete
        """
        response = await self.client.get(
            f"/{self.API_VERSION}/image-to-3d/{task_id}",
        )
        
        if response.status_code != 200:
            raise MeshyAPIError(
                f"Failed to get task status: {response.text}",
                status_code=response.status_code,
            )
        
        data = response.json()
        
        # Parse status
        status_str = data.get("status", "PENDING").upper()
        try:
            status = TaskStatus(status_str)
        except ValueError:
            status = TaskStatus.PENDING
        
        # Extract model URLs
        model_urls = {}
        if "model_urls" in data:
            model_urls = data["model_urls"]
        
        # Extract texture URLs
        texture_urls = data.get("texture_urls", [])
        
        return MeshResult(
            task_id=task_id,
            status=status,
            model_urls=model_urls,
            thumbnail_url=data.get("thumbnail_url", ""),
            texture_urls=texture_urls,
            progress=data.get("progress", 0),
            metadata={"raw_response": data},
        )
    
    async def wait_for_completion(
        self,
        task_id: str,
        timeout: int | None = None,
        poll_interval: float = 5.0,
        on_progress: callable = None,
    ) -> MeshResult:
        """
        Wait for a task to complete.
        
        Args:
            task_id: The task ID to wait for
            timeout: Maximum seconds to wait (default from config)
            poll_interval: Seconds between status checks
            on_progress: Callback(progress: int) for progress updates
            
        Returns:
            MeshResult when complete
            
        Raises:
            TimeoutError: If task doesn't complete in time
            MeshyAPIError: If task fails
        """
        timeout = timeout or self.config.mesh_timeout_seconds
        start_time = time.time()
        last_progress = -1
        
        while True:
            result = await self.get_task_status(task_id)
            
            # Report progress
            if on_progress and result.progress != last_progress:
                on_progress(result.progress)
                last_progress = result.progress
            
            # Check completion
            if result.is_complete:
                result.finished_at = datetime.now()
                return result
            
            if result.is_failed:
                raise MeshyAPIError(
                    f"Task failed with status: {result.status.value}",
                    response=result.metadata.get("raw_response"),
                )
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Task {task_id} did not complete within {timeout}s"
                )
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
    
    async def download(
        self,
        result: MeshResult,
        output_dir: Path,
        format: Literal["stl", "obj", "fbx", "glb"] = "stl",
    ) -> Path:
        """
        Download the generated mesh.
        
        Args:
            result: Completed MeshResult
            output_dir: Directory to save to
            format: File format to download
            
        Returns:
            Path to downloaded file
        """
        url = result.model_urls.get(format)
        if not url:
            available = list(result.model_urls.keys())
            raise ValueError(
                f"Format '{format}' not available. Available: {available}"
            )
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{result.task_id}.{format}"
        output_path = output_dir / filename
        
        # Download file
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            output_path.write_bytes(response.content)
        
        return output_path
    
    async def from_image_async(
        self,
        image_url: str,
        options: MeshOptions | None = None,
        output_dir: Path | None = None,
        format: Literal["stl", "obj", "fbx", "glb"] = "stl",
        on_progress: callable = None,
    ) -> MeshResult:
        """
        Full async pipeline: create task, wait, download.
        
        Args:
            image_url: URL of the source image
            options: Mesh generation options
            output_dir: Directory to save mesh (optional)
            format: Output format
            on_progress: Progress callback
            
        Returns:
            MeshResult with local_path if output_dir specified
        """
        # Create task
        task_id = await self.create_task(image_url, options)
        
        # Wait for completion
        result = await self.wait_for_completion(
            task_id,
            on_progress=on_progress,
        )
        
        # Download if output dir specified
        if output_dir:
            result.local_path = await self.download(result, output_dir, format)
        
        return result
    
    def from_image(
        self,
        image_url: str,
        options: MeshOptions | None = None,
        output_dir: Path | None = None,
        format: Literal["stl", "obj", "fbx", "glb"] = "stl",
        on_progress: callable = None,
    ) -> MeshResult:
        """
        Synchronous wrapper for from_image_async.
        """
        return asyncio.run(
            self.from_image_async(image_url, options, output_dir, format, on_progress)
        )


# Convenience function
def image_to_3d(
    image_url: str,
    output_dir: Path | None = None,
    format: str = "stl",
) -> MeshResult:
    """
    Quick function to convert image to 3D.
    
    Example:
        >>> from print3d.mesh_gen import image_to_3d
        >>> result = image_to_3d("https://example.com/robot.png", output_dir="./models")
        >>> print(result.local_path)
    """
    gen = MeshGenerator()
    return gen.from_image(image_url, output_dir=output_dir, format=format)


__all__ = [
    "MeshGenerator",
    "MeshResult",
    "MeshOptions",
    "MeshTopology",
    "TaskStatus",
    "MeshyAPIError",
    "image_to_3d",
]
