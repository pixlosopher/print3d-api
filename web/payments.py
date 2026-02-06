"""
Payment integration for Print3D.

Supports Stripe for checkout.
"""

from __future__ import annotations

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stripe
from dataclasses import dataclass
from typing import Literal

from config import Config, get_config

logger = logging.getLogger(__name__)


@dataclass
class CheckoutSession:
    """Result from creating a checkout session."""
    session_id: str
    checkout_url: str
    provider: Literal["stripe"]


@dataclass
class PaymentResult:
    """Result from a completed payment."""
    payment_id: str
    order_id: str
    amount_cents: int
    currency: str
    status: Literal["succeeded", "pending", "failed"]
    provider: Literal["stripe"]
    customer_email: str


# Pricing configuration
PRICING = {
    "small": {"pla": 2900, "resin": 3900},   # cents
    "medium": {"pla": 4900, "resin": 5900},
    "large": {"pla": 6900, "resin": 8900},
}

SIZE_LABELS = {
    "small": "Small (50mm)",
    "medium": "Medium (75mm)",
    "large": "Large (100mm)",
}

MATERIAL_LABELS = {
    "pla": "PLA Plastic",
    "resin": "Premium Resin",
}


class PaymentService:
    """Handle Stripe payments."""

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()

        # Initialize Stripe with active key (respects STRIPE_MODE)
        if self.config.has_stripe:
            stripe.api_key = self.config.active_stripe_secret_key
            if self.config.is_stripe_test_mode:
                logger.info("[Stripe] Running in TEST mode")

    def get_price(self, size: str, material: str) -> int:
        """Get price in cents for a size/material combination."""
        return PRICING.get(size, {}).get(material, 4900)

    def create_stripe_checkout(
        self,
        order_id: str,
        job_id: str,
        size: str,
        material: str,
        customer_email: str,
        shipping_address: dict,
        price_cents: int | None = None,
    ) -> CheckoutSession:
        """Create a Stripe Checkout session."""
        if not self.config.has_stripe:
            raise ValueError("Stripe not configured")

        # Use provided price_cents, or fall back to legacy pricing
        if price_cents is None:
            price_cents = self.get_price(size, material)

        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            customer_email=customer_email,
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": price_cents,
                        "product_data": {
                            "name": f"3D Print - {SIZE_LABELS.get(size, size)}",
                            "description": f"Material: {MATERIAL_LABELS.get(material, material)}",
                        },
                    },
                    "quantity": 1,
                },
            ],
            shipping_address_collection={
                "allowed_countries": [
                    # North America
                    "US", "CA", "MX",
                    # Europe
                    "GB", "DE", "FR", "ES", "IT", "NL", "BE", "AT", "CH", "SE", "DK", "NO", "FI", "IE", "PT", "PL",
                    # Asia Pacific
                    "AU", "NZ", "JP", "SG", "HK",
                    # South America
                    "BR", "AR", "CL", "CO",
                ],
            },
            metadata={
                "order_id": order_id,
                "job_id": job_id,
                "size": size,
                "material": material,
            },
            success_url=f"{self.config.frontend_url}/order/success?order_id={order_id}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{self.config.frontend_url}/create?cancelled=true",
        )

        return CheckoutSession(
            session_id=session.id,
            checkout_url=session.url,
            provider="stripe",
        )

    def verify_stripe_webhook(self, payload: bytes, signature: str) -> dict:
        """Verify and parse Stripe webhook."""
        webhook_secret = self.config.active_stripe_webhook_secret
        if not webhook_secret:
            raise ValueError("Stripe webhook secret not configured")

        event = stripe.Webhook.construct_event(
            payload,
            signature,
            webhook_secret,
        )
        return event

    def handle_payment_success(self, event: dict) -> PaymentResult:
        """Handle successful payment from webhook."""
        session = event["data"]["object"]

        return PaymentResult(
            payment_id=session["payment_intent"],
            order_id=session["metadata"]["order_id"],
            amount_cents=session["amount_total"],
            currency=session["currency"],
            status="succeeded",
            provider="stripe",
            customer_email=session["customer_email"],
        )


# Convenience function
def get_payment_service() -> PaymentService:
    """Get payment service instance."""
    return PaymentService()


__all__ = [
    "PaymentService",
    "CheckoutSession",
    "PaymentResult",
    "PRICING",
    "get_payment_service",
]
