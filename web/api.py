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

# Import new pricing/options modules
from sizes import get_sizes_dict, get_all_sizes, get_size
from materials import get_materials_dict, get_all_materials, get_material, get_color_for_material
from mesh_options import get_mesh_styles_dict, get_all_mesh_styles, MeshGenerationOptions
from pricing import calculate_price, get_price_matrix, validate_order_config

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


# ============ Options & Pricing (NEW) ============

@app.route("/api/options")
def get_options():
    """
    Get all available customization options.

    Returns sizes, materials, and mesh styles for the UI.
    """
    return jsonify({
        "sizes": get_sizes_dict(),
        "materials": get_materials_dict(),
        "mesh_styles": get_mesh_styles_dict(),
        "price_matrix": get_price_matrix(),
    })


@app.route("/api/price", methods=["POST"])
def get_price():
    """
    Calculate price for a specific configuration.

    Request body:
        - material: Material key (e.g., "plastic_white")
        - size: Size key (e.g., "medium")
        - color: Optional color key

    Returns price breakdown with total.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    material_key = data.get("material")
    size_key = data.get("size")
    color_key = data.get("color")

    if not material_key or not size_key:
        return jsonify({
            "error": "Missing required fields",
            "required": ["material", "size"]
        }), 400

    # Validate configuration
    is_valid, error_msg = validate_order_config(material_key, size_key, color_key)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    try:
        breakdown = calculate_price(material_key, size_key, color_key)
        return jsonify(breakdown.to_dict())
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/generate", methods=["POST"])
def generate_concept():
    """
    Generate a 2D concept image only (no 3D yet).

    This is the new cost-efficient flow:
    1. Generate 2D image (cheap: ~$0.001)
    2. User reviews and selects options
    3. User pays
    4. Only then generate 3D (expensive: ~$0.30)

    Request body:
        - prompt: Text description
        - style: Optional style (default: "figurine")

    Returns:
        - job_id: For tracking
        - image_url: Preview image
        - status: "concept_ready"
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    prompt = data.get("prompt") or data.get("description")
    if not prompt:
        return jsonify({
            "error": "Missing required field: prompt",
            "required": ["prompt"]
        }), 400

    style = data.get("style", "figurine")

    if not job_service:
        return jsonify({"error": "Generation service not available"}), 503

    try:
        # Submit job for 2D generation only
        job_id = job_service.submit_concept_job(
            agent_name="web_client",
            description=prompt,
            style=style,
        )

        return jsonify({
            "success": True,
            "job_id": job_id,
            "status": "generating_concept",
            "message": "Generando concepto 2D...",
            "status_url": f"/api/jobs/{job_id}",
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/validate-config", methods=["POST"])
def validate_config():
    """
    Validate an order configuration before checkout.

    Checks that material, size, and color combination is valid.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    material_key = data.get("material")
    size_key = data.get("size")
    color_key = data.get("color")
    mesh_style = data.get("mesh_style", "detailed")

    is_valid, error_msg = validate_order_config(material_key, size_key, color_key)

    if not is_valid:
        return jsonify({
            "valid": False,
            "error": error_msg,
        }), 400

    # Also validate mesh style exists
    if mesh_style not in ["detailed", "stylized"]:
        return jsonify({
            "valid": False,
            "error": f"Invalid mesh_style: {mesh_style}. Use 'detailed' or 'stylized'.",
        }), 400

    # Get price for valid config
    breakdown = calculate_price(material_key, size_key, color_key)

    return jsonify({
        "valid": True,
        "price": breakdown.to_dict(),
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
    """
    Create a checkout session for an order.

    Request body:
        - job_id: Job ID from /api/generate
        - email: Customer email
        - size: Size key (mini, small, medium, large, xl)
        - material: Material key (plastic_white, plastic_color, etc.)
        - color: Optional color key (if material supports colors)
        - mesh_style: Optional mesh style (detailed, stylized)
        - shipping_address: Optional shipping address dict
        - provider: Payment provider (stripe, paypal)
    """
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
    color = data.get("color")
    mesh_style = data.get("mesh_style", "detailed")
    shipping_address = data.get("shipping_address", {})
    provider = data.get("provider", "stripe")

    # Validate configuration using new pricing system
    is_valid, error_msg = validate_order_config(material, size, color)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    # Get price using new pricing system
    try:
        price_breakdown = calculate_price(material, size, color)
        price_cents = price_breakdown.total_cents
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Create order with new fields
    order = order_service.create_order(
        job_id=job_id,
        customer_email=email,
        size=size,
        material=material,
        color=color,
        mesh_style=mesh_style,
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
                price_cents=price_cents,
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

def resolve_mesh_path(mesh_path_str: str) -> Path:
    """Resolve mesh path from job to actual file path."""
    # mesh_path could be:
    # - "/output/xxx.glb" (API format)
    # - "output/xxx.glb" (relative)
    # - Full absolute path

    # First try as-is if it starts with /app (Render deployment)
    if mesh_path_str.startswith("/app/"):
        return Path(mesh_path_str)

    # Extract just the filename part
    if mesh_path_str.startswith("/output/"):
        filename = mesh_path_str.replace("/output/", "")
    elif mesh_path_str.startswith("output/"):
        filename = mesh_path_str.replace("output/", "")
    else:
        filename = Path(mesh_path_str).name

    # Try config.output_dir first
    local_path = Path(config.output_dir) / filename
    if local_path.exists():
        return local_path

    # Try /app/output (Render production)
    render_path = Path("/app/output") / filename
    if render_path.exists():
        return render_path

    # Fall back to config.output_dir (even if doesn't exist, for error message)
    return local_path


def submit_to_shapeways(order):
    """Helper to submit an order to Shapeways."""
    try:
        if shapeways_service.is_available:
            job = job_service.get_job_status(order.job_id)
            if job and job.get("mesh_path"):
                mesh_path = resolve_mesh_path(job["mesh_path"])
                if mesh_path.exists():
                    # Build shipping address dict for Shapeways
                    shipping_address = None
                    if hasattr(order, 'shipping_address') and order.shipping_address:
                        addr = order.shipping_address
                        if hasattr(addr, 'to_dict'):
                            shipping_address = addr.to_dict()
                        elif isinstance(addr, dict):
                            shipping_address = addr

                    shapeways_result = shapeways_service.submit_order(
                        mesh_path=mesh_path,
                        material=order.material,
                        shipping_address=shipping_address,
                    )
                    if shapeways_result.success:
                        order_service.update_shapeways_id(
                            order_id=order.id,
                            shapeways_order_id=shapeways_result.shapeways_order_id,
                        )
                        print(f"[Shapeways] Order created: {shapeways_result.shapeways_order_id}")
                    else:
                        print(f"[Shapeways] Failed: {shapeways_result.error_message}")
                else:
                    print(f"[Shapeways] Mesh not found: {mesh_path}")
            else:
                print(f"[Shapeways] No mesh_path in job {order.job_id}")
        else:
            print("[Shapeways] Service not available")
    except Exception as e:
        import traceback
        print(f"[Shapeways] Error: {e}")
        traceback.print_exc()


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
        payment_result = payment_service.handle_payment_success(event)

        # Update order status
        order_service.mark_paid(
            order_id=payment_result.order_id,
            payment_id=payment_result.payment_id,
            payment_provider="stripe",
        )

        # Get order details for processing
        order = order_service.get_order(payment_result.order_id)
        if order:
            # Send confirmation email
            try:
                if email_service.is_available:
                    email_result = email_service.send_order_confirmation(
                        to_email=order.customer_email,
                        order_id=order.id,
                        order_details={
                            "size": order.size,
                            "material": order.material,
                            "color": getattr(order, 'color', None),
                            "mesh_style": getattr(order, 'mesh_style', 'detailed'),
                            "price": f"${order.price_cents / 100:.2f}",
                        }
                    )
                    if email_result.success:
                        print(f"[Webhook] Confirmation email sent to {order.customer_email}")
                    else:
                        print(f"[Webhook] Email failed: {email_result.error}")
            except Exception as e:
                print(f"[Webhook] Failed to send email: {e}")

            # Check if job is concept_only (needs 3D generation)
            job = job_service.get_job_status(order.job_id)
            if job:
                is_concept_only = job.get("concept_only", False) or job.get("status") == "concept_ready"

                if is_concept_only:
                    # NEW FLOW: Generate 3D now that payment is confirmed
                    print(f"[Webhook] Generating 3D for concept job {order.job_id}...")
                    mesh_style = getattr(order, 'mesh_style', 'detailed')
                    material_key = order.material

                    # Generate mesh in background (don't block webhook)
                    # Capture order_id to reload fresh order in thread
                    order_id_for_thread = order.id
                    job_id_for_thread = order.job_id

                    import threading
                    def generate_and_submit():
                        try:
                            print(f"[Webhook Thread] Starting 3D generation for {job_id_for_thread}...")
                            success = job_service.generate_mesh_for_job(
                                job_id=job_id_for_thread,
                                mesh_style=mesh_style,
                                material_key=material_key,
                            )
                            if success:
                                print(f"[Webhook Thread] 3D generated for {job_id_for_thread}")
                                # Reload order from DB to get fresh session
                                fresh_order = order_service.get_order(order_id_for_thread)
                                if fresh_order:
                                    print(f"[Webhook Thread] Submitting to Shapeways...")
                                    submit_to_shapeways(fresh_order)
                                else:
                                    print(f"[Webhook Thread] ERROR: Could not reload order {order_id_for_thread}")
                            else:
                                print(f"[Webhook Thread] 3D generation failed for {job_id_for_thread}")
                        except Exception as e:
                            import traceback
                            print(f"[Webhook Thread] Error: {e}")
                            traceback.print_exc()

                    thread = threading.Thread(target=generate_and_submit, daemon=True)
                    thread.start()
                else:
                    # OLD FLOW: Mesh already exists, submit to Shapeways
                    submit_to_shapeways(order)

        return jsonify({"status": "success", "order_id": payment_result.order_id})

    return jsonify({"status": "ignored"})


@app.route("/api/webhook/paypal", methods=["POST"])
def paypal_webhook():
    """Handle PayPal webhook events."""
    data = request.get_json()
    # TODO: Implement PayPal webhook handling
    return jsonify({"status": "received"})


# ============ Admin ============

@app.route("/api/admin/process-order/<order_id>", methods=["POST"])
def admin_process_order(order_id: str):
    """Manually process an order (mark as paid and send to Shapeways)."""
    # Simple auth check - require admin_key in header
    admin_key = request.headers.get("X-Admin-Key")
    if admin_key != "print3d-admin-2024":
        return jsonify({"error": "Unauthorized"}), 401

    # Get order
    order = order_service.get_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    results = {"order_id": order_id, "steps": []}

    # Mark as paid
    try:
        order_service.mark_paid(
            order_id=order_id,
            payment_id="manual_" + order_id,
            payment_provider="manual",
        )
        results["steps"].append({"step": "mark_paid", "status": "success"})
    except Exception as e:
        results["steps"].append({"step": "mark_paid", "status": "error", "error": str(e)})

    # Submit to Shapeways
    try:
        if shapeways_service.is_available:
            job = job_service.get_job_status(order.job_id)
            if job and job.get("mesh_path"):
                mesh_path = resolve_mesh_path(job["mesh_path"])
                if mesh_path.exists():
                    # Build shipping address for Shapeways
                    shipping_address = None
                    if hasattr(order, 'shipping_address') and order.shipping_address:
                        addr = order.shipping_address
                        if hasattr(addr, 'to_dict'):
                            shipping_address = addr.to_dict()
                        elif isinstance(addr, dict):
                            shipping_address = addr

                    shapeways_result = shapeways_service.submit_order(
                        mesh_path=mesh_path,
                        material=order.material,
                        shipping_address=shipping_address,
                    )
                    if shapeways_result.success:
                        order_service.update_shapeways_id(
                            order_id=order.id,
                            shapeways_order_id=shapeways_result.shapeways_order_id,
                        )
                        results["steps"].append({
                            "step": "shapeways",
                            "status": "success",
                            "shapeways_order_id": shapeways_result.shapeways_order_id
                        })
                    else:
                        results["steps"].append({
                            "step": "shapeways",
                            "status": "error",
                            "error": shapeways_result.error_message
                        })
                else:
                    results["steps"].append({
                        "step": "shapeways",
                        "status": "error",
                        "error": f"Mesh file not found: {mesh_path}"
                    })
            else:
                results["steps"].append({
                    "step": "shapeways",
                    "status": "error",
                    "error": "No mesh_path in job"
                })
        else:
            results["steps"].append({
                "step": "shapeways",
                "status": "skipped",
                "reason": "Shapeways not configured"
            })
    except Exception as e:
        results["steps"].append({"step": "shapeways", "status": "error", "error": str(e)})

    return jsonify(results)


@app.route("/api/admin/regenerate-3d/<order_id>", methods=["POST"])
def admin_regenerate_3d(order_id: str):
    """Regenerate 3D model for an order and submit to Shapeways."""
    admin_key = request.headers.get("X-Admin-Key")
    if admin_key != "print3d-admin-2024":
        return jsonify({"error": "Unauthorized"}), 401

    order = order_service.get_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    results = {"order_id": order_id, "job_id": order.job_id, "steps": []}

    # Step 1: Regenerate 3D
    try:
        mesh_style = getattr(order, 'mesh_style', 'detailed')
        material_key = order.material

        print(f"[Admin] Regenerating 3D for job {order.job_id}...")
        success = job_service.generate_mesh_for_job(
            job_id=order.job_id,
            mesh_style=mesh_style,
            material_key=material_key,
        )

        if success:
            results["steps"].append({"step": "generate_3d", "status": "success"})
        else:
            results["steps"].append({"step": "generate_3d", "status": "error", "error": "Generation failed"})
            return jsonify(results)

    except Exception as e:
        results["steps"].append({"step": "generate_3d", "status": "error", "error": str(e)})
        return jsonify(results)

    # Step 2: Submit to Shapeways
    try:
        # Reload order to get fresh data
        order = order_service.get_order(order_id)
        job = job_service.get_job_status(order.job_id)

        if job and job.get("mesh_path"):
            mesh_path = resolve_mesh_path(job["mesh_path"])
            if mesh_path.exists():
                shipping_address = None
                if hasattr(order, 'shipping_address') and order.shipping_address:
                    addr = order.shipping_address
                    if hasattr(addr, 'to_dict'):
                        shipping_address = addr.to_dict()
                    elif isinstance(addr, dict):
                        shipping_address = addr

                shapeways_result = shapeways_service.submit_order(
                    mesh_path=mesh_path,
                    material=order.material,
                    shipping_address=shipping_address,
                )

                if shapeways_result.success:
                    order_service.update_shapeways_id(
                        order_id=order.id,
                        shapeways_order_id=shapeways_result.shapeways_order_id,
                    )
                    results["steps"].append({
                        "step": "shapeways",
                        "status": "success",
                        "shapeways_order_id": shapeways_result.shapeways_order_id
                    })
                else:
                    results["steps"].append({
                        "step": "shapeways",
                        "status": "error",
                        "error": shapeways_result.error_message
                    })
            else:
                results["steps"].append({
                    "step": "shapeways",
                    "status": "error",
                    "error": f"Mesh file not found: {mesh_path}"
                })
        else:
            results["steps"].append({
                "step": "shapeways",
                "status": "error",
                "error": "No mesh_path after generation"
            })

    except Exception as e:
        import traceback
        traceback.print_exc()
        results["steps"].append({"step": "shapeways", "status": "error", "error": str(e)})

    return jsonify(results)


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
