"""
3D Printing API module for print3d pipeline.

Integrates with Shapeways API for uploading models and ordering prints.
"""

from __future__ import annotations

import asyncio
import httpx
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

try:
    from .config import Config, get_config
except ImportError:
    from config import Config, get_config


@dataclass
class Material:
    """Available print material."""
    id: str
    name: str
    color: str
    finish: str
    price: float
    currency: str = "USD"
    min_wall_thickness_mm: float = 0.0
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "finish": self.finish,
            "price": self.price,
            "currency": self.currency,
            "min_wall_thickness_mm": self.min_wall_thickness_mm,
            "description": self.description,
        }


@dataclass
class ModelUpload:
    """Result of model upload."""
    model_id: str
    filename: str
    file_version: int
    volume_cm3: float | None
    surface_area_cm2: float | None
    bounding_box: dict | None
    is_printable: bool
    printability_issues: list[str] = field(default_factory=list)
    uploaded_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "filename": self.filename,
            "file_version": self.file_version,
            "volume_cm3": self.volume_cm3,
            "surface_area_cm2": self.surface_area_cm2,
            "bounding_box": self.bounding_box,
            "is_printable": self.is_printable,
            "printability_issues": self.printability_issues,
            "uploaded_at": self.uploaded_at.isoformat(),
        }


@dataclass
class PricingResult:
    """Pricing information for a model."""
    model_id: str
    materials: list[Material]
    cheapest: Material | None = None
    fastest: Material | None = None
    
    def get_by_name(self, name: str) -> Material | None:
        """Find material by name (case-insensitive)."""
        name_lower = name.lower()
        for m in self.materials:
            if m.name.lower() == name_lower:
                return m
        return None
    
    def filter_by_price(self, max_price: float) -> list[Material]:
        """Get materials under price limit."""
        return [m for m in self.materials if m.price <= max_price]
    
    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "materials": [m.to_dict() for m in self.materials],
            "cheapest": self.cheapest.to_dict() if self.cheapest else None,
        }


@dataclass 
class CartItem:
    """Item in shopping cart."""
    model_id: str
    material_id: str
    quantity: int = 1


@dataclass
class Order:
    """Placed order."""
    order_id: str
    status: str
    items: list[dict]
    total: float
    currency: str
    shipping_address: dict | None
    created_at: datetime
    
    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "status": self.status,
            "items": self.items,
            "total": self.total,
            "currency": self.currency,
            "created_at": self.created_at.isoformat(),
        }


class ShapewaysError(Exception):
    """Error from Shapeways API."""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class PrintService:
    """
    Interface to 3D printing service (Shapeways).
    
    Example:
        >>> service = PrintService()
        >>> upload = service.upload("model.stl")
        >>> pricing = service.get_pricing(upload.model_id)
        >>> print(f"Cheapest: ${pricing.cheapest.price}")
    """
    
    API_VERSION = "v1"
    
    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self._client: httpx.AsyncClient | None = None
        self._access_token: str | None = None
        self._token_expires: datetime | None = None
        
        if not self.config.has_shapeways:
            raise ValueError(
                "Shapeways API not configured. "
                "Set SHAPEWAYS_CLIENT_ID and SHAPEWAYS_CLIENT_SECRET."
            )
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialized HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.shapeways_base_url,
                timeout=120.0,  # Uploads can be slow
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _ensure_token(self):
        """Ensure we have a valid access token."""
        if self._access_token and self._token_expires:
            if datetime.now() < self._token_expires:
                return  # Token still valid
        
        # Get new token
        response = await self.client.post(
            "/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.config.shapeways_client_id,
                "client_secret": self.config.shapeways_client_secret,
            },
        )
        
        if response.status_code != 200:
            raise ShapewaysError(
                f"Failed to get access token: {response.text}",
                status_code=response.status_code,
            )
        
        data = response.json()
        self._access_token = data["access_token"]
        # Set expiry with buffer
        expires_in = data.get("expires_in", 3600)
        from datetime import timedelta
        self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
    
    async def _request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """Make authenticated request."""
        await self._ensure_token()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._access_token}"

        # Shapeways API uses /endpoint/v1 format, not /v1/endpoint
        response = await self.client.request(
            method,
            path,
            headers=headers,
            **kwargs,
        )

        if response.status_code >= 400:
            raise ShapewaysError(
                f"API error: {response.text}",
                status_code=response.status_code,
                response=response.json() if response.content else None,
            )

        return response
    
    async def upload_async(
        self,
        file_path: Path | str,
        filename: str | None = None,
        has_rights: bool = True,
        description: str = "3D model uploaded via API",
    ) -> ModelUpload:
        """
        Upload a 3D model file.

        Args:
            file_path: Path to STL/OBJ/GLB file
            filename: Display name (defaults to file name)
            has_rights: Confirm you have rights to print this model
            description: Model description (required by Shapeways)

        Returns:
            ModelUpload with model ID and analysis results
        """
        import base64

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        filename = filename or file_path.name

        # Read and encode file as base64 (required by Shapeways API)
        file_data = file_path.read_bytes()
        file_base64 = base64.b64encode(file_data).decode("utf-8")

        # Upload using JSON body with base64-encoded file
        # Shapeways API format: /models/v1
        response = await self._request(
            "POST",
            "/models/v1",
            json={
                "fileName": filename,
                "file": file_base64,
                "description": description,
                "hasRightsToModel": 1,
                "acceptTermsAndConditions": 1,
            },
        )
        
        data = response.json()
        
        # Parse response
        model_data = data.get("model", data)
        
        # Check printability
        is_printable = model_data.get("isPrintable", True)
        issues = []
        if "printabilityIssues" in model_data:
            issues = model_data["printabilityIssues"]
        
        return ModelUpload(
            model_id=str(model_data.get("modelId", "")),
            filename=filename,
            file_version=model_data.get("fileVersion", 1),
            volume_cm3=model_data.get("volume"),
            surface_area_cm2=model_data.get("surfaceArea"),
            bounding_box=model_data.get("boundingBox"),
            is_printable=is_printable,
            printability_issues=issues,
            metadata={"raw_response": data},
        )
    
    async def get_pricing_async(self, model_id: str) -> PricingResult:
        """
        Get pricing for all available materials.

        Args:
            model_id: The model ID from upload

        Returns:
            PricingResult with material options and prices
        """
        # Shapeways API format: /models/{modelId}/v1
        response = await self._request(
            "GET",
            f"/models/{model_id}/v1",
        )
        
        data = response.json()
        
        materials = []
        for item in data.get("prices", []):
            material = Material(
                id=str(item.get("materialId", "")),
                name=item.get("material", "Unknown"),
                color=item.get("color", ""),
                finish=item.get("finish", ""),
                price=float(item.get("price", 0)),
                currency=item.get("currency", "USD"),
                min_wall_thickness_mm=float(item.get("minimumWallThickness", 0)),
            )
            materials.append(material)
        
        # Sort by price
        materials.sort(key=lambda m: m.price)
        
        cheapest = materials[0] if materials else None
        
        return PricingResult(
            model_id=model_id,
            materials=materials,
            cheapest=cheapest,
        )
    
    async def add_to_cart_async(
        self,
        items: list[CartItem],
    ) -> dict:
        """
        Add items to shopping cart.

        Args:
            items: List of CartItem objects

        Returns:
            Cart data
        """
        cart_items = [
            {
                "modelId": item.model_id,
                "materialId": item.material_id,
                "quantity": item.quantity,
            }
            for item in items
        ]

        # Note: Shapeways cart API may not be directly available
        # This is a placeholder - actual ordering uses /orders/v1
        response = await self._request(
            "POST",
            "/cart/v1",
            json={"items": cart_items},
        )

        return response.json()

    async def get_cart_async(self) -> dict:
        """Get current cart contents."""
        response = await self._request("GET", "/cart/v1")
        return response.json()

    async def create_order_async(
        self,
        items: list[CartItem],
        shipping_address: dict,
        shipping_option: str = "Cheapest",
    ) -> dict:
        """
        Create an order on Shapeways.

        Args:
            items: List of CartItem objects
            shipping_address: Dict with firstName, lastName, country, state,
                             city, address1, zipCode, phoneNumber
            shipping_option: Shipping method (default: Cheapest)

        Returns:
            Order data with orderId
        """
        order_items = [
            {
                "modelId": item.model_id,
                "materialId": item.material_id,
                "quantity": item.quantity,
            }
            for item in items
        ]

        order_data = {
            "items": order_items,
            "firstName": shipping_address.get("firstName", ""),
            "lastName": shipping_address.get("lastName", ""),
            "country": shipping_address.get("country", "US"),
            "state": shipping_address.get("state", ""),
            "city": shipping_address.get("city", ""),
            "address1": shipping_address.get("address1", ""),
            "address2": shipping_address.get("address2", ""),
            "zipCode": shipping_address.get("zipCode", ""),
            "phoneNumber": shipping_address.get("phoneNumber", ""),
            "shippingOption": shipping_option,
            "paymentMethod": "credit_card",
        }

        response = await self._request(
            "POST",
            "/orders/v1",
            json=order_data,
        )

        return response.json()
    
    # Synchronous wrappers
    def upload(
        self,
        file_path: Path | str,
        filename: str | None = None,
        has_rights: bool = True,
    ) -> ModelUpload:
        """Synchronous wrapper for upload_async."""
        return asyncio.run(self.upload_async(file_path, filename, has_rights))
    
    def get_pricing(self, model_id: str) -> PricingResult:
        """Synchronous wrapper for get_pricing_async."""
        return asyncio.run(self.get_pricing_async(model_id))
    
    def add_to_cart(self, items: list[CartItem]) -> dict:
        """Synchronous wrapper for add_to_cart_async."""
        return asyncio.run(self.add_to_cart_async(items))


# Convenience functions
def upload_model(file_path: Path | str) -> ModelUpload:
    """
    Quick function to upload a model.
    
    Example:
        >>> from print3d.print_api import upload_model
        >>> upload = upload_model("robot.stl")
        >>> print(upload.model_id)
    """
    service = PrintService()
    return service.upload(file_path)


def get_print_pricing(model_id: str) -> PricingResult:
    """
    Quick function to get pricing.
    
    Example:
        >>> from print3d.print_api import get_print_pricing
        >>> pricing = get_print_pricing("12345")
        >>> print(f"Cheapest: ${pricing.cheapest.price}")
    """
    service = PrintService()
    return service.get_pricing(model_id)


__all__ = [
    # Service
    "PrintService",
    # Data classes
    "Material",
    "ModelUpload",
    "PricingResult",
    "CartItem",
    "Order",
    # Errors
    "ShapewaysError",
    # Convenience
    "upload_model",
    "get_print_pricing",
]
