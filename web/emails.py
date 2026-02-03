"""
Email notifications for Print3D.

Uses Resend for transactional emails.
"""

from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass
from typing import Optional

from config import Config, get_config


@dataclass
class EmailResult:
    """Result from sending an email."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class EmailService:
    """Send transactional emails via Resend."""

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self._client = None

        if self.config.has_email:
            try:
                import resend
                resend.api_key = self.config.resend_api_key
                self._client = resend
            except ImportError:
                pass

    @property
    def is_available(self) -> bool:
        """Check if email service is configured."""
        return self._client is not None

    def _send(self, to: str, subject: str, html: str) -> EmailResult:
        """Send an email."""
        if not self._client:
            return EmailResult(success=False, error="Email not configured")

        try:
            result = self._client.Emails.send({
                "from": self.config.from_email,
                "to": to,
                "subject": subject,
                "html": html,
            })
            return EmailResult(success=True, message_id=result.get("id"))
        except Exception as e:
            return EmailResult(success=False, error=str(e))

    def send_order_confirmation(
        self,
        to_email: str,
        order_id: str,
        order_details: dict,
    ) -> EmailResult:
        """Send order confirmation email.

        Args:
            to_email: Customer email
            order_id: Order ID
            order_details: Dict with size, material, price
        """
        size = order_details.get("size", "Unknown")
        material = order_details.get("material", "Unknown")
        price = order_details.get("price", "$0.00")
        to = to_email

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: system-ui, sans-serif; background: #0a0a0a; color: #ffffff; padding: 40px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #1a1a1a; border-radius: 16px; padding: 32px; }}
                .header {{ text-align: center; margin-bottom: 24px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #10b981; }}
                h1 {{ color: #ffffff; font-size: 28px; margin-bottom: 16px; }}
                .order-box {{ background: #2a2a2a; border-radius: 12px; padding: 24px; margin: 24px 0; }}
                .order-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #333; }}
                .order-row:last-child {{ border-bottom: none; }}
                .label {{ color: #888; }}
                .value {{ color: #fff; font-weight: 500; }}
                .total {{ font-size: 24px; color: #10b981; font-weight: bold; }}
                .button {{ display: inline-block; background: #10b981; color: #000; padding: 16px 32px; border-radius: 9999px; text-decoration: none; font-weight: 600; margin-top: 24px; }}
                .footer {{ text-align: center; margin-top: 32px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🖨️ Print3D</div>
                </div>
                <h1>Order Confirmed!</h1>
                <p style="color: #888;">Thank you for your order. We're preparing your custom 3D print.</p>

                <div class="order-box">
                    <div class="order-row">
                        <span class="label">Order ID</span>
                        <span class="value">{order_id}</span>
                    </div>
                    <div class="order-row">
                        <span class="label">Size</span>
                        <span class="value">{size}</span>
                    </div>
                    <div class="order-row">
                        <span class="label">Material</span>
                        <span class="value">{material}</span>
                    </div>
                    <div class="order-row">
                        <span class="label">Total</span>
                        <span class="total">{price}</span>
                    </div>
                </div>

                <p style="color: #888;">Your 3D print is now in production. We'll send you an email with tracking information once it ships.</p>

                <div style="text-align: center;">
                    <a href="{self.config.frontend_url}/order/{order_id}" class="button">Track Your Order</a>
                </div>

                <div class="footer">
                    <p>Questions? Reply to this email or visit our website.</p>
                    <p>© 2026 Print3D. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return self._send(to, f"Order Confirmed - #{order_id}", html)

    def send_shipping_notification(
        self,
        to: str,
        order_id: str,
        tracking_number: str,
        carrier: str = "USPS",
    ) -> EmailResult:
        """Send shipping notification email."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: system-ui, sans-serif; background: #0a0a0a; color: #ffffff; padding: 40px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #1a1a1a; border-radius: 16px; padding: 32px; }}
                .header {{ text-align: center; margin-bottom: 24px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #10b981; }}
                h1 {{ color: #ffffff; font-size: 28px; margin-bottom: 16px; }}
                .tracking-box {{ background: #10b981; color: #000; border-radius: 12px; padding: 24px; margin: 24px 0; text-align: center; }}
                .tracking-number {{ font-size: 28px; font-weight: bold; font-family: monospace; }}
                .button {{ display: inline-block; background: #10b981; color: #000; padding: 16px 32px; border-radius: 9999px; text-decoration: none; font-weight: 600; margin-top: 24px; }}
                .footer {{ text-align: center; margin-top: 32px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🖨️ Print3D</div>
                </div>
                <h1>Your Order Has Shipped! 📦</h1>
                <p style="color: #888;">Great news! Your custom 3D print is on its way.</p>

                <div class="tracking-box">
                    <div style="margin-bottom: 8px;">Tracking Number ({carrier})</div>
                    <div class="tracking-number">{tracking_number}</div>
                </div>

                <p style="color: #888;">Expected delivery: 3-5 business days</p>

                <div style="text-align: center;">
                    <a href="{self.config.frontend_url}/order/{order_id}" class="button">Track Package</a>
                </div>

                <div class="footer">
                    <p>© 2026 Print3D. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return self._send(to, f"Your Order Has Shipped! - #{order_id}", html)


# Singleton
_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Get email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


__all__ = ["EmailService", "EmailResult", "get_email_service"]
