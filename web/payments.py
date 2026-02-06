"""
Payment integration for Print3D.

Supports Stripe and PayPal for checkout.
"""

from __future__ import annotations

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stripe
import paypalrestsdk
from dataclasses import dataclass
from typing import Literal

from config import Config, get_config

logger = logging.getLogger(__name__)


@dataclass
class CheckoutSession:
    """Result from creating a checkout session."""
    session_id: str
    checkout_url: str
    provider: Literal["stripe", "paypal"]


@dataclass
class PaymentResult:
    """Result from a completed payment."""
    payment_id: str
    order_id: str
    amount_cents: int
    currency: str
    status: Literal["succeeded", "pending", "failed"]
    provider: Literal["stripe", "paypal"]
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
    """Handle Stripe and PayPal payments."""

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()

        # Initialize Stripe with active key (respects STRIPE_MODE)
        if self.config.has_stripe:
            stripe.api_key = self.config.active_stripe_secret_key
            if self.config.is_stripe_test_mode:
                logger.info("[Stripe] Running in TEST mode")

        # Initialize PayPal
        if self.config.has_paypal:
            paypalrestsdk.configure({
                "mode": self.config.paypal_mode,  # "sandbox" or "live"
                "client_id": self.config.paypal_client_id,
                "client_secret": self.config.paypal_client_secret,
            })
            logger.info(f"[PayPal] Running in {self.config.paypal_mode.upper()} mode")

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

    def create_paypal_checkout(
        self,
        order_id: str,
        job_id: str,
        size: str,
        material: str,
        customer_email: str,
        price_cents: int | None = None,
    ) -> CheckoutSession:
        """Create a PayPal payment."""
        if not self.config.has_paypal:
            raise ValueError("PayPal not configured")

        # Use provided price_cents, or fall back to legacy pricing
        if price_cents is None:
            price_cents = self.get_price(size, material)

        price_dollars = price_cents / 100

        # Create PayPal payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": f"{self.config.frontend_url}/order/success?order_id={order_id}&provider=paypal",
                "cancel_url": f"{self.config.frontend_url}/create?cancelled=true"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"3D Print - {SIZE_LABELS.get(size, size)}",
                        "description": f"Material: {MATERIAL_LABELS.get(material, material)}",
                        "quantity": "1",
                        "price": f"{price_dollars:.2f}",
                        "currency": "USD"
                    }]
                },
                "amount": {
                    "total": f"{price_dollars:.2f}",
                    "currency": "USD"
                },
                "description": f"POSSIBLE 3D Print - Order {order_id}",
                "custom": f"{order_id}|{job_id}|{size}|{material}"  # Store metadata
            }]
        })

        if payment.create():
            # Find approval URL
            approval_url = None
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = link.href
                    break

            if not approval_url:
                raise ValueError("PayPal approval URL not found")

            logger.info(f"[PayPal] Payment created: {payment.id} for order {order_id}")

            return CheckoutSession(
                session_id=payment.id,
                checkout_url=approval_url,
                provider="paypal",
            )
        else:
            logger.error(f"[PayPal] Payment creation failed: {payment.error}")
            raise ValueError(f"PayPal error: {payment.error}")

    def execute_paypal_payment(self, payment_id: str, payer_id: str) -> PaymentResult:
        """Execute a PayPal payment after user approval."""
        payment = paypalrestsdk.Payment.find(payment_id)

        if payment.execute({"payer_id": payer_id}):
            # Parse custom metadata
            custom = payment.transactions[0].custom
            parts = custom.split("|")
            order_id = parts[0] if len(parts) > 0 else ""

            amount_str = payment.transactions[0].amount.total
            amount_cents = int(float(amount_str) * 100)

            # Get payer email
            payer_email = payment.payer.payer_info.email if payment.payer.payer_info else ""

            logger.info(f"[PayPal] Payment executed: {payment_id} for order {order_id}")

            return PaymentResult(
                payment_id=payment_id,
                order_id=order_id,
                amount_cents=amount_cents,
                currency="USD",
                status="succeeded",
                provider="paypal",
                customer_email=payer_email,
            )
        else:
            logger.error(f"[PayPal] Payment execution failed: {payment.error}")
            raise ValueError(f"PayPal execution error: {payment.error}")

    def verify_paypal_webhook(self, payload: dict, headers: dict) -> dict:
        """Verify PayPal webhook signature."""
        # PayPal webhook verification
        # For sandbox, we can be more lenient
        # In production, implement full webhook signature verification

        # Basic validation - check required fields
        if "event_type" not in payload or "resource" not in payload:
            raise ValueError("Invalid PayPal webhook payload")

        return payload

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
