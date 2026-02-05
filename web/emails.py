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
        to_email: str,
        order_id: str,
        tracking_number: str,
        tracking_url: str = "",
        carrier: str = "USPS",
    ) -> EmailResult:
        """Send shipping notification email.

        Args:
            to_email: Customer email
            order_id: Order ID
            tracking_number: Carrier tracking number
            tracking_url: Optional direct tracking URL
            carrier: Carrier name for display
        """
        # If tracking_url provided, use it; otherwise default to order page
        track_button_url = tracking_url if tracking_url else f"{self.config.frontend_url}/order/{order_id}"
        track_button_text = "Track Package" if tracking_url else "View Order"

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
                .order-info {{ background: #2a2a2a; border-radius: 12px; padding: 16px; margin: 16px 0; }}
                .button {{ display: inline-block; background: #10b981; color: #000; padding: 16px 32px; border-radius: 9999px; text-decoration: none; font-weight: 600; margin-top: 24px; }}
                .footer {{ text-align: center; margin-top: 32px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">✨ POSSIBLE</div>
                </div>
                <h1>¡Tu Orden Ha Sido Enviada! 📦</h1>
                <p style="color: #888;">¡Excelentes noticias! Tu impresión 3D personalizada está en camino.</p>

                <div class="tracking-box">
                    <div style="margin-bottom: 8px;">Número de Rastreo</div>
                    <div class="tracking-number">{tracking_number}</div>
                </div>

                <div class="order-info">
                    <p style="margin: 0; color: #888;"><strong style="color: #fff;">Orden:</strong> #{order_id}</p>
                    <p style="margin: 8px 0 0 0; color: #888;"><strong style="color: #fff;">Entrega estimada:</strong> 5-10 días hábiles</p>
                </div>

                <div style="text-align: center;">
                    <a href="{track_button_url}" class="button">{track_button_text}</a>
                </div>

                <div class="footer">
                    <p>¿Preguntas? Responde a este email.</p>
                    <p>© 2026 POSSIBLE. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return self._send(to_email, f"¡Tu Orden Ha Sido Enviada! - #{order_id}", html)

    def send_model_ready_notification(
        self,
        to_email: str,
        order_id: str,
        order_url: str = "",
    ) -> EmailResult:
        """Send notification when 3D model is ready.

        Args:
            to_email: Customer email
            order_id: Order ID
            order_url: URL to view the order/model
        """
        view_url = order_url if order_url else f"{self.config.frontend_url}/order/{order_id}"

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
                .status-box {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #000; border-radius: 12px; padding: 24px; margin: 24px 0; text-align: center; }}
                .status-icon {{ font-size: 48px; margin-bottom: 12px; }}
                .status-text {{ font-size: 18px; font-weight: 600; }}
                .order-info {{ background: #2a2a2a; border-radius: 12px; padding: 16px; margin: 16px 0; }}
                .button {{ display: inline-block; background: #10b981; color: #000; padding: 16px 32px; border-radius: 9999px; text-decoration: none; font-weight: 600; margin-top: 24px; }}
                .footer {{ text-align: center; margin-top: 32px; color: #666; font-size: 14px; }}
                .steps {{ background: #2a2a2a; border-radius: 12px; padding: 20px; margin: 24px 0; }}
                .step {{ display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid #333; }}
                .step:last-child {{ border-bottom: none; }}
                .step-icon {{ width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 12px; font-size: 14px; }}
                .step-done {{ background: #10b981; color: #000; }}
                .step-current {{ background: #f59e0b; color: #000; }}
                .step-pending {{ background: #333; color: #666; }}
                .step-text {{ color: #888; }}
                .step-text.active {{ color: #fff; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">✨ POSSIBLE</div>
                </div>
                <h1>¡Tu Modelo 3D Está Listo! 🎉</h1>
                <p style="color: #888;">Hemos generado tu modelo 3D personalizado. Ahora está listo para impresión.</p>

                <div class="status-box">
                    <div class="status-icon">🎨</div>
                    <div class="status-text">Modelo 3D Generado Exitosamente</div>
                </div>

                <div class="steps">
                    <div class="step">
                        <div class="step-icon step-done">✓</div>
                        <span class="step-text active">Pago confirmado</span>
                    </div>
                    <div class="step">
                        <div class="step-icon step-done">✓</div>
                        <span class="step-text active">Modelo 3D generado</span>
                    </div>
                    <div class="step">
                        <div class="step-icon step-current">⏳</div>
                        <span class="step-text active">Preparando impresión</span>
                    </div>
                    <div class="step">
                        <div class="step-icon step-pending">4</div>
                        <span class="step-text">Envío</span>
                    </div>
                </div>

                <div class="order-info">
                    <p style="margin: 0; color: #888;"><strong style="color: #fff;">Orden:</strong> #{order_id}</p>
                    <p style="margin: 8px 0 0 0; color: #888;">Puedes ver tu modelo 3D en el enlace de abajo.</p>
                </div>

                <div style="text-align: center;">
                    <a href="{view_url}" class="button">Ver Mi Modelo 3D</a>
                </div>

                <div class="footer">
                    <p>Te notificaremos cuando tu pedido sea enviado.</p>
                    <p>¿Preguntas? Responde a este email.</p>
                    <p>© 2026 POSSIBLE. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return self._send(to_email, f"¡Tu Modelo 3D Está Listo! - #{order_id}", html)


# Singleton
_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Get email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


__all__ = ["EmailService", "EmailResult", "get_email_service"]
