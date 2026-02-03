"""
Order management for Print3D.

Handles order lifecycle from creation to fulfillment with database persistence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from web.database import (
    get_db_session,
    create_order as db_create_order,
    get_order as db_get_order,
    update_order as db_update_order,
    list_orders_by_email as db_list_orders_by_email,
    OrderModel,
    OrderStatusEnum,
)


class OrderStatus(str, Enum):
    """Order lifecycle states."""
    PENDING_PAYMENT = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    PRINTING = "printing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass
class ShippingAddress:
    """Customer shipping address."""
    name: str
    address_line1: str
    address_line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
        }


@dataclass
class Order:
    """Customer order (in-memory representation for compatibility)."""
    id: str
    job_id: str
    customer_email: str
    size: str
    material: str
    price_cents: int
    status: OrderStatus
    shipping_address: ShippingAddress
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    tracking_number: Optional[str] = None
    shapeways_order_id: Optional[str] = None
    payment_id: Optional[str] = None
    payment_provider: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "customer_email": self.customer_email,
            "size": self.size,
            "material": self.material,
            "price_cents": self.price_cents,
            "price_display": f"${self.price_cents / 100:.2f}",
            "status": self.status.value,
            "shipping_address": self.shipping_address.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "tracking_number": self.tracking_number,
            "shapeways_order_id": self.shapeways_order_id,
        }

    @classmethod
    def from_db_model(cls, model: OrderModel) -> "Order":
        """Create Order from database model."""
        address = ShippingAddress(
            name=model.shipping_name or "",
            address_line1=model.shipping_address or "",
            city=model.shipping_city or "",
            state=model.shipping_state or "",
            postal_code=model.shipping_zip or "",
            country=model.shipping_country or "US",
        )

        # Map database status to OrderStatus enum
        status_map = {
            "pending": OrderStatus.PENDING_PAYMENT,
            "paid": OrderStatus.PAID,
            "processing": OrderStatus.PROCESSING,
            "shipped": OrderStatus.SHIPPED,
            "delivered": OrderStatus.DELIVERED,
            "cancelled": OrderStatus.CANCELLED,
            "refunded": OrderStatus.REFUNDED,
        }
        status = status_map.get(model.status, OrderStatus.PENDING_PAYMENT)

        return cls(
            id=model.id,
            job_id=model.job_id,
            customer_email=model.email,
            size=model.size,
            material=model.material,
            price_cents=int(model.price_usd * 100),
            status=status,
            shipping_address=address,
            created_at=model.created_at or datetime.now(),
            updated_at=model.updated_at or datetime.now(),
            tracking_number=model.tracking_number,
            shapeways_order_id=model.shapeways_order_id,
            payment_id=model.payment_intent_id,
            payment_provider=model.payment_provider,
        )


class OrderService:
    """Manage orders with database persistence."""

    def __init__(self):
        pass  # No more in-memory storage needed

    def create_order(
        self,
        job_id: str,
        customer_email: str,
        size: str,
        material: str,
        price_cents: int,
        shipping_address: dict,
    ) -> Order:
        """Create a new order."""
        order_id = str(uuid.uuid4())[:8].upper()

        with get_db_session() as db:
            db_model = db_create_order(
                db=db,
                order_id=order_id,
                job_id=job_id,
                email=customer_email,
                size=size,
                material=material,
                price_usd=price_cents / 100.0,
                shipping={
                    "name": shipping_address.get("name", ""),
                    "address": shipping_address.get("address", ""),
                    "city": shipping_address.get("city", ""),
                    "state": shipping_address.get("state", ""),
                    "zip": shipping_address.get("zip", ""),
                    "country": shipping_address.get("country", "US"),
                },
            )
            return Order.from_db_model(db_model)

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        with get_db_session() as db:
            model = db_get_order(db, order_id)
            if not model:
                return None
            return Order.from_db_model(model)

    def update_order_status(
        self,
        order_id: str,
        status: OrderStatus,
        **kwargs,
    ) -> Optional[Order]:
        """Update order status."""
        with get_db_session() as db:
            update_data = {"status": status.value}

            if status == OrderStatus.PAID:
                update_data["payment_intent_id"] = kwargs.get("payment_id")
                update_data["payment_provider"] = kwargs.get("payment_provider")

            if status == OrderStatus.SHIPPED:
                update_data["tracking_number"] = kwargs.get("tracking_number")

            model = db_update_order(db, order_id, **update_data)
            if not model:
                return None
            return Order.from_db_model(model)

    def mark_paid(
        self,
        order_id: str,
        payment_id: str,
        payment_provider: str,
    ) -> Optional[Order]:
        """Mark order as paid."""
        return self.update_order_status(
            order_id,
            OrderStatus.PAID,
            payment_id=payment_id,
            payment_provider=payment_provider,
        )

    def mark_shipped(
        self,
        order_id: str,
        tracking_number: str,
    ) -> Optional[Order]:
        """Mark order as shipped."""
        return self.update_order_status(
            order_id,
            OrderStatus.SHIPPED,
            tracking_number=tracking_number,
        )

    def get_orders_by_email(self, email: str) -> list[Order]:
        """Get all orders for a customer email."""
        with get_db_session() as db:
            models = db_list_orders_by_email(db, email)
            return [Order.from_db_model(m) for m in models]

    def get_pending_orders(self) -> list[Order]:
        """Get orders that need processing."""
        # This would need a custom query
        # For now, return empty list
        return []

    def update_shapeways_id(
        self,
        order_id: str,
        shapeways_order_id: str,
    ) -> Optional[Order]:
        """Update order with Shapeways order ID."""
        with get_db_session() as db:
            model = db_update_order(
                db, order_id,
                shapeways_order_id=shapeways_order_id,
                status=OrderStatusEnum.PROCESSING.value,
            )
            if not model:
                return None
            return Order.from_db_model(model)


# Singleton instance
_order_service: OrderService | None = None


def get_order_service() -> OrderService:
    """Get order service singleton."""
    global _order_service
    if _order_service is None:
        _order_service = OrderService()
    return _order_service


__all__ = [
    "Order",
    "OrderStatus",
    "OrderService",
    "ShippingAddress",
    "get_order_service",
]
