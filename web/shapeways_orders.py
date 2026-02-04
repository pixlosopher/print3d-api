"""
Shapeways order management for Print3D.

Handles uploading models and creating orders after payment.
"""

from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from config import get_config

# Try to import PrintService
try:
    from print_api import PrintService, CartItem, ShapewaysError
except ImportError:
    try:
        from ..print_api import PrintService, CartItem, ShapewaysError
    except ImportError:
        PrintService = None
        CartItem = None
        ShapewaysError = Exception


@dataclass
class ShapewaysOrderResult:
    """Result from Shapeways order submission."""
    success: bool
    shapeways_model_id: Optional[str] = None
    shapeways_order_id: Optional[str] = None
    error_message: Optional[str] = None
    is_printable: bool = True
    printability_issues: list = None

    def __post_init__(self):
        if self.printability_issues is None:
            self.printability_issues = []


class ShapewaysOrderService:
    """
    Manages Shapeways order workflow:
    1. Upload mesh file to Shapeways
    2. Add to cart with selected material
    3. Create order
    """

    # Map our material names to Shapeways material IDs
    # These IDs come from Shapeways API - you may need to update them
    MATERIAL_MAP = {
        "pla": "6",       # White Strong & Flexible (nylon, closest to PLA)
        "resin": "25",    # Frosted Ultra Detail (resin)
    }

    def __init__(self):
        self.config = get_config()
        self._print_service = None

    @property
    def print_service(self) -> PrintService:
        """Lazy load print service."""
        if self._print_service is None:
            if PrintService is None:
                raise ValueError("PrintService not available")
            self._print_service = PrintService(self.config)
        return self._print_service

    @property
    def is_available(self) -> bool:
        """Check if Shapeways is configured."""
        return self.config.has_shapeways and PrintService is not None

    async def upload_model_async(self, mesh_path: Path | str) -> ShapewaysOrderResult:
        """
        Upload a mesh file to Shapeways.

        Args:
            mesh_path: Path to the GLB/STL file

        Returns:
            ShapewaysOrderResult with model_id if successful
        """
        if not self.is_available:
            return ShapewaysOrderResult(
                success=False,
                error_message="Shapeways not configured"
            )

        mesh_path = Path(mesh_path)
        if not mesh_path.exists():
            return ShapewaysOrderResult(
                success=False,
                error_message=f"Mesh file not found: {mesh_path}"
            )

        try:
            print(f"[Shapeways] Uploading mesh: {mesh_path} ({mesh_path.stat().st_size / 1024:.1f} KB)")
            upload = await self.print_service.upload_async(mesh_path)
            print(f"[Shapeways] Upload success: model_id={upload.model_id}, printable={upload.is_printable}")

            return ShapewaysOrderResult(
                success=True,
                shapeways_model_id=upload.model_id,
                is_printable=upload.is_printable,
                printability_issues=upload.printability_issues,
            )

        except ShapewaysError as e:
            print(f"[Shapeways] Upload API Error: {e.message} (status: {e.status_code})")
            if e.response:
                print(f"[Shapeways] Response: {e.response}")
            return ShapewaysOrderResult(
                success=False,
                error_message=f"Shapeways upload failed: {e.message}"
            )
        except Exception as e:
            import traceback
            print(f"[Shapeways] Upload Exception: {str(e)}")
            traceback.print_exc()
            return ShapewaysOrderResult(
                success=False,
                error_message=f"Upload error: {str(e)}"
            )

    async def create_order_async(
        self,
        model_id: str,
        material: str,
        shipping_address: dict = None,
        quantity: int = 1,
    ) -> ShapewaysOrderResult:
        """
        Create an order on Shapeways.

        Args:
            model_id: Shapeways model ID from upload
            material: Our material name (pla, resin, plastic_white, etc.)
            shipping_address: Dict with name, address, city, state, zip, country, phone
            quantity: Number of prints

        Returns:
            ShapewaysOrderResult with order_id if successful
        """
        if not self.is_available:
            return ShapewaysOrderResult(
                success=False,
                error_message="Shapeways not configured"
            )

        # Map our material to Shapeways material ID
        # Extended mapping for new material keys
        extended_material_map = {
            **self.MATERIAL_MAP,
            "plastic_white": "6",      # White Strong & Flexible
            "plastic_color": "62",     # Strong & Flexible - colored
            "resin_premium": "25",     # Frosted Ultra Detail
            "full_color": "26",        # Full Color Sandstone
            "metal_steel": "81",       # Stainless Steel
        }
        material_key = material.lower().replace("-", "_")
        material_id = extended_material_map.get(material_key, "6")

        try:
            cart_item = CartItem(
                model_id=model_id,
                material_id=material_id,
                quantity=quantity,
            )

            # If we have shipping address, create full order
            if shipping_address:
                # Parse name into first/last
                full_name = shipping_address.get("name", "Customer")
                name_parts = full_name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                shapeways_address = {
                    "firstName": first_name,
                    "lastName": last_name,
                    "address1": shipping_address.get("address_line1", shipping_address.get("address", "")),
                    "address2": shipping_address.get("address_line2", ""),
                    "city": shipping_address.get("city", ""),
                    "state": shipping_address.get("state", ""),
                    "zipCode": shipping_address.get("postal_code", shipping_address.get("zip", "")),
                    "country": shipping_address.get("country", "US"),
                    "phoneNumber": shipping_address.get("phone", ""),
                }

                print(f"[Shapeways] Creating order with address: {shapeways_address}")
                order_result = await self.print_service.create_order_async(
                    items=[cart_item],
                    shipping_address=shapeways_address,
                )
                print(f"[Shapeways] Order result: {order_result}")

                return ShapewaysOrderResult(
                    success=True,
                    shapeways_model_id=model_id,
                    shapeways_order_id=str(order_result.get("orderId", order_result.get("result", {}).get("orderId", "unknown"))),
                )
            else:
                # Fallback: just add to cart if no shipping address
                cart_result = await self.print_service.add_to_cart_async([cart_item])
                return ShapewaysOrderResult(
                    success=True,
                    shapeways_model_id=model_id,
                    shapeways_order_id=cart_result.get("cartId", "cart_added"),
                )

        except ShapewaysError as e:
            print(f"[Shapeways] API Error: {e.message} (status: {e.status_code})")
            if e.response:
                print(f"[Shapeways] Response: {e.response}")
            return ShapewaysOrderResult(
                success=False,
                error_message=f"Shapeways order failed: {e.message}"
            )
        except Exception as e:
            import traceback
            print(f"[Shapeways] Exception: {str(e)}")
            traceback.print_exc()
            return ShapewaysOrderResult(
                success=False,
                error_message=f"Order error: {str(e)}"
            )

    async def submit_order_async(
        self,
        mesh_path: Path | str,
        material: str,
        shipping_address: dict = None,
        quantity: int = 1,
    ) -> ShapewaysOrderResult:
        """
        Full workflow: upload mesh and create order.

        Args:
            mesh_path: Path to mesh file
            material: Material name (pla, resin, plastic_white, etc.)
            shipping_address: Dict with shipping details
            quantity: Number of prints

        Returns:
            ShapewaysOrderResult with model_id and order_id
        """
        # Step 1: Upload model
        upload_result = await self.upload_model_async(mesh_path)
        if not upload_result.success:
            return upload_result

        if not upload_result.is_printable:
            return ShapewaysOrderResult(
                success=False,
                shapeways_model_id=upload_result.shapeways_model_id,
                error_message=f"Model not printable: {upload_result.printability_issues}",
                is_printable=False,
                printability_issues=upload_result.printability_issues,
            )

        # Step 2: Create order with shipping address
        order_result = await self.create_order_async(
            model_id=upload_result.shapeways_model_id,
            material=material,
            shipping_address=shipping_address,
            quantity=quantity,
        )

        return order_result

    # Sync wrappers - handle event loop properly for thread contexts
    def _run_async(self, coro):
        """Run an async coroutine, handling event loop conflicts."""
        # Always create a fresh event loop for this thread
        # This avoids issues with closed loops or running loops in Flask threads
        try:
            # Create new event loop for this thread
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        except Exception as e:
            print(f"[Shapeways] _run_async error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def upload_model(self, mesh_path: Path | str) -> ShapewaysOrderResult:
        """Sync wrapper for upload_model_async."""
        return self._run_async(self.upload_model_async(mesh_path))

    def create_order(self, model_id: str, material: str, shipping_address: dict = None, quantity: int = 1) -> ShapewaysOrderResult:
        """Sync wrapper for create_order_async."""
        return self._run_async(self.create_order_async(model_id, material, shipping_address, quantity))

    def submit_order(self, mesh_path: Path | str, material: str, shipping_address: dict = None, quantity: int = 1) -> ShapewaysOrderResult:
        """Sync wrapper for submit_order_async."""
        return self._run_async(self.submit_order_async(mesh_path, material, shipping_address, quantity))


# Singleton
_shapeways_service: Optional[ShapewaysOrderService] = None


def get_shapeways_service() -> ShapewaysOrderService:
    """Get Shapeways service singleton."""
    global _shapeways_service
    if _shapeways_service is None:
        _shapeways_service = ShapewaysOrderService()
    return _shapeways_service


__all__ = [
    "ShapewaysOrderService",
    "ShapewaysOrderResult",
    "get_shapeways_service",
]
