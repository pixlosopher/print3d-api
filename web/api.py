"""
REST API for Print3D web frontend.

Provides endpoints for:
- Job submission and status
- Checkout and payment
- Order tracking

Version: 1.0.1 - Environment variables fix
"""

from __future__ import annotations

import os
import sys

# Add directories to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
web_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, parent_dir)
sys.path.insert(0, web_dir)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path

# Import config
from config import get_config

# Import local modules
from orders import get_order_service, OrderStatus
from payments import get_payment_service, PRICING
from job_service import get_job_service
from shapeways_orders import get_shapeways_service
from emails import get_email_service

# Create Flask app
app = Flask(__name__)

# Enable CORS for frontend
CORS(app, origins=["http://localhost:3000", "https://*.vercel.app", "*"])

# Services
config = get_config()
order_service = get_order_service()
payment_service = get_payment_service()
job_service = get_job_service()  # Real Gemini + Meshy pipeline
shapeways_service = get_shapeways_service()
email_service = get_email_service()


# ============ Health & Config ============

@app.route("/")
def index():
    """Root endpoint."""
    return jsonify({
        "name": "Print3D API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "jobs": "/api/jobs",
            "checkout": "/api/checkout",
            "orders": "/api/order/<id>",
        }
    })


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "services": {
            "meshy": config.has_meshy,
            "shapeways": config.has_shapeways,
            "stripe": config.has_stripe,
            "paypal": config.has_paypal,
            "email": config.has_email,
            "image_gen": config.has_image_gen,
        }
    })


@app.route("/api/config")
def get_public_config():
    """Get public configuration for frontend."""
    return jsonify({
        "stripe_publishable_key": config.stripe_publishable_key if config.has_stripe else None,
        "paypal_client_id": config.paypal_client_id if config.has_paypal else None,
        "pricing": PRICING,
    })


# ============ Job Management ============

@app.route("/api/jobs", methods=["POST"])
def create_job():
    """Submit a new 3D generation job."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    required = ["description"]
    if not all(field in data for field in required):
        return jsonify({"error": "Missing required fields", "required": required}), 400

    description = data["description"]
    style = data.get("style", "figurine")
    size_mm = data.get("size_mm", 50.0)

    if not job_service:
        return jsonify({"error": "Job service not available"}), 503

    try:
        job_id = job_service.submit_job(
            agent_name="web_client",
            description=description,
            style=style,
            size_mm=size_mm,
        )

        return jsonify({
            "success": True,
            "job_id": job_id,
            "message": "Job submitted successfully",
            "status_url": f"/api/jobs/{job_id}",
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/jobs/<job_id>")
def get_job(job_id: str):
    """Get job status and results."""
    if not job_service:
        return jsonify({"error": "Job service not available"}), 503

    job = job_service.get_job_status(job_id)

    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job)


@app.route("/api/jobs")
def list_jobs():
    """List recent jobs."""
    if not job_service:
        return jsonify({"error": "Job service not available"}), 503

    agent_name = request.args.get("agent_name")
    limit = int(request.args.get("limit", 20))

    jobs = job_service.list_jobs(agent_name, limit)

    return jsonify({"jobs": jobs, "total": len(jobs)})


# ============ Checkout ============

@app.route("/api/checkout", methods=["POST"])
def create_checkout():
    """Create a checkout session for an order."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    required = ["job_id", "email", "size", "material"]
    if not all(field in data for field in required):
        return jsonify({"error": "Missing required fields", "required": required}), 400

    job_id = data["job_id"]
    email = data["email"]
    size = data["size"]
    material = data["material"]
    shipping_address = data.get("shipping_address", {})
    provider = data.get("provider", "stripe")

    # Get price
    price_cents = payment_service.get_price(size, material)

    # Create order
    order = order_service.create_order(
        job_id=job_id,
        customer_email=email,
        size=size,
        material=material,
        price_cents=price_cents,
        shipping_address=shipping_address,
    )

    try:
        if provider == "stripe" and config.has_stripe:
            session = payment_service.create_stripe_checkout(
                order_id=order.id,
                job_id=job_id,
                size=size,
                material=material,
                customer_email=email,
                shipping_address=shipping_address,
            )
            return jsonify({
                "success": True,
                "order_id": order.id,
                "checkout_url": session.checkout_url,
                "session_id": session.session_id,
                "provider": "stripe",
            })
        elif provider == "paypal" and config.has_paypal:
            session = payment_service.create_paypal_checkout(
                order_id=order.id,
                job_id=job_id,
                size=size,
                material=material,
                customer_email=email,
            )
            return jsonify({
                "success": True,
                "order_id": order.id,
                "checkout_url": session.checkout_url,
                "provider": "paypal",
            })
        else:
            return jsonify({
                "error": "No payment provider configured",
                "order_id": order.id,
            }), 503

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ Webhooks ============

@app.route("/api/webhook/stripe", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.data
    signature = request.headers.get("Stripe-Signature")

    # For local testing without webhook secret, skip verification
    if not config.stripe_webhook_secret:
        import json
        try:
            event = json.loads(payload)
        except:
            return jsonify({"error": "Invalid JSON"}), 400
    else:
        try:
            event = payment_service.verify_stripe_webhook(payload, signature)
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    if event["type"] == "checkout.session.completed":
        result = payment_service.handle_payment_success(event)

        # Update order status
        order_service.mark_paid(
            order_id=result.order_id,
            payment_id=result.payment_id,
            payment_provider="stripe",
        )

        # Get order details for email and Shapeways
        order = order_service.get_order(result.order_id)
        if order:
            # Send confirmation email
            try:
                if email_service.is_available:
                    result = email_service.send_order_confirmation(
                        to_email=order.customer_email,
                        order_id=order.id,
                        order_details={
                            "size": order.size,
                            "material": order.material,
                            "price": f"${order.price_cents / 100:.2f}",
                        }
                    )
                    if result.success:
                        print(f"[Webhook] Confirmation email sent to {order.customer_email}")
                    else:
                        print(f"[Webhook] Email failed: {result.error}")
            except Exception as e:
                print(f"[Webhook] Failed to send email: {e}")

            # Submit to Shapeways
            try:
                if shapeways_service.is_available:
                    # Get mesh path from job
                    job = job_service.get_job_status(order.job_id)
                    if job and job.get("mesh_path"):
                        mesh_path = Path(config.output_dir) / job["mesh_path"].replace("/output/", "")
                        if mesh_path.exists():
                            shapeways_result = shapeways_service.submit_order(
                                mesh_path=mesh_path,
                                material=order.material,
                            )
                            if shapeways_result.success:
                                order_service.update_shapeways_id(
                                    order_id=order.id,
                                    shapeways_order_id=shapeways_result.shapeways_order_id,
                                )
                                print(f"[Webhook] Shapeways order created: {shapeways_result.shapeways_order_id}")
                            else:
                                print(f"[Webhook] Shapeways failed: {shapeways_result.error_message}")
            except Exception as e:
                print(f"[Webhook] Shapeways error: {e}")

        return jsonify({"status": "success", "order_id": result.order_id})

    return jsonify({"status": "ignored"})


@app.route("/api/webhook/paypal", methods=["POST"])
def paypal_webhook():
    """Handle PayPal webhook events."""
    data = request.get_json()
    # TODO: Implement PayPal webhook handling
    return jsonify({"status": "received"})


# ============ Orders ============

@app.route("/api/order/<order_id>")
def get_order(order_id: str):
    """Get order details."""
    order = order_service.get_order(order_id)

    if not order:
        return jsonify({"error": "Order not found"}), 404

    return jsonify(order.to_dict())


@app.route("/api/orders")
def list_orders():
    """List orders for an email."""
    email = request.args.get("email")

    if not email:
        return jsonify({"error": "Email required"}), 400

    orders = order_service.get_orders_by_email(email)

    return jsonify({
        "orders": [o.to_dict() for o in orders],
        "total": len(orders),
    })


# ============ Static Files ============

@app.route("/output/<path:filename>")
def serve_output(filename: str):
    """Serve generated files."""
    output_dir = Path(config.output_dir).resolve()
    return send_from_directory(output_dir, filename)


@app.route("/agent_output/<path:filename>")
def serve_agent_output(filename: str):
    """Serve agent output files."""
    output_dir = Path("./agent_output").resolve()
    return send_from_directory(output_dir, filename)


# ============ Main ============

def create_app():
    """Create and configure the Flask app."""
    return app


def main():
    """Run the API server."""
    import os
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    print("=" * 50)
    print("🚀 Starting Print3D API Server")
    print("=" * 50)
    print(f"   Port: {port}")
    print(f"   Debug: {debug}")
    print(f"   Frontend URL: {config.frontend_url}")
    print(f"   Gemini: {'✅' if config.has_image_gen else '❌'}")
    print(f"   Meshy: {'✅' if config.has_meshy else '❌'}")
    print(f"   Stripe: {'✅' if config.has_stripe else '❌'}")
    print(f"   PayPal: {'✅' if config.has_paypal else '❌'}")
    print(f"   Shapeways: {'✅' if config.has_shapeways else '❌'}")
    print("=" * 50)

    # Start job worker if available
    if job_service:
        job_service.start_worker()
        print("✅ Job worker started")

    app.run(host="0.0.0.0", port=port, debug=debug)


# Start worker on import for gunicorn
if job_service:
    job_service.start_worker()


if __name__ == "__main__":
    main()
