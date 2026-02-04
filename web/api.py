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

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from pathlib import Path
from datetime import datetime

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
            "stripe_mode": config.stripe_mode,  # "live" or "test"
            "paypal": config.has_paypal,
            "email": config.has_email,
            "image_gen": config.has_image_gen,
        }
    })


@app.route("/api/config")
def get_public_config():
    """Get public configuration for frontend."""
    return jsonify({
        "stripe_publishable_key": config.active_stripe_publishable_key if config.has_stripe else None,
        "stripe_mode": config.stripe_mode,  # "live" or "test"
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


# ============ Regional Pricing ============

@app.route("/api/pricing/<country_code>")
def get_regional_pricing(country_code: str):
    """
    Get prices for a specific country.

    Prices vary by region (USA/Canada vs LATAM).
    Also returns local currency equivalent for display.

    Args:
        country_code: ISO 3166-1 alpha-2 code (e.g., "MX", "US", "AR")

    Returns:
        Price table with all sizes for that country.
    """
    from regional_pricing import get_price_table

    try:
        price_table = get_price_table(country_code)
        return jsonify(price_table)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/pricing/<country_code>/<size_key>")
def get_regional_price_for_size(country_code: str, size_key: str):
    """
    Get price for a specific size and country.

    Args:
        country_code: ISO 3166-1 alpha-2 code (e.g., "MX", "US")
        size_key: Size key (mini, small, medium, large)

    Returns:
        Price details for that specific configuration.
    """
    from regional_pricing import calculate_price as calc_regional_price

    try:
        price_result = calc_regional_price(size_key, country_code)
        return jsonify(price_result.to_dict())
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/pricing/custom", methods=["POST"])
def get_custom_height_price():
    """
    Calculate price for a custom height.

    Request body:
        - height_mm: Desired height in millimeters (30-300mm)
        - country_code: ISO 3166-1 alpha-2 code (e.g., "MX", "US")

    Returns:
        Price details for custom height.
    """
    from regional_pricing import get_region_for_country, PRICES, SIZES
    from mesh_scaler import calculate_price_for_height, get_preset_or_custom_price

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    height_mm = data.get("height_mm")
    country_code = data.get("country_code", "MX")

    if height_mm is None:
        return jsonify({"error": "height_mm is required"}), 400

    try:
        height_mm = float(height_mm)
    except (TypeError, ValueError):
        return jsonify({"error": "height_mm must be a number"}), 400

    # Constrain to reasonable range
    if height_mm < 30 or height_mm > 300:
        return jsonify({
            "error": "height_mm must be between 30 and 300mm",
            "min": 30,
            "max": 300,
        }), 400

    # Get region and base price
    region = get_region_for_country(country_code)
    base_price = PRICES[region.key]["mini"]
    base_height = SIZES["mini"].height_mm

    # Calculate custom price
    price_cents = calculate_price_for_height(
        height_mm=height_mm,
        base_price_cents=base_price,
        base_height_mm=base_height,
    )

    return jsonify({
        "height_mm": height_mm,
        "country_code": country_code.upper(),
        "region": {
            "key": region.key,
            "name": region.name,
            "name_es": region.name_es,
        },
        "price_cents": price_cents,
        "price_usd": price_cents / 100,
        "price_display": f"${price_cents / 100:.0f}",
        "is_custom": True,
        "constraints": {
            "min_height_mm": 30,
            "max_height_mm": 300,
        },
    })


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
        - size: Size key (mini, small, medium, large, xl) or "custom"
        - material: Material key (plastic_white, plastic_color, etc.)
        - color: Optional color key (if material supports colors)
        - mesh_style: Optional mesh style (detailed, stylized)
        - shipping_address: Optional shipping address dict
        - provider: Payment provider (stripe, paypal)
        - custom_height_mm: Required if size is "custom" (30-300mm)
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
    custom_height_mm = data.get("custom_height_mm")

    # Get country from shipping address for regional pricing
    shipping_country = shipping_address.get("country", "US").upper()

    # Handle custom size vs preset sizes
    try:
        if size == "custom":
            # Validate custom height
            if not custom_height_mm:
                return jsonify({"error": "custom_height_mm required for custom size"}), 400

            try:
                custom_height_mm = float(custom_height_mm)
            except (TypeError, ValueError):
                return jsonify({"error": "custom_height_mm must be a number"}), 400

            if custom_height_mm < 30 or custom_height_mm > 300:
                return jsonify({"error": "custom_height_mm must be between 30 and 300mm"}), 400

            # Calculate custom price
            from mesh_scaler import calculate_price_for_height
            from regional_pricing import get_region_for_country, PRICES, SIZES

            region = get_region_for_country(shipping_country)
            base_price = PRICES[region.key]["mini"]
            base_height = SIZES["mini"].height_mm

            price_cents = calculate_price_for_height(
                height_mm=custom_height_mm,
                base_price_cents=base_price,
                base_height_mm=base_height,
            )
            print(f"[Checkout] Custom size: {custom_height_mm}mm, Region: {region.key}, Country: {shipping_country}, Price: ${price_cents/100}")

            # Store custom height in size field for order
            size = f"custom_{int(custom_height_mm)}mm"
        else:
            # Use standard regional pricing
            from regional_pricing import calculate_price as calc_regional_price
            regional_price = calc_regional_price(size, shipping_country)
            price_cents = regional_price.price_cents
            print(f"[Checkout] Region: {regional_price.region_key}, Country: {shipping_country}, Size: {size}, Price: ${price_cents/100}")
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


# ============ Admin Dashboard (Semi-Manual Workflow) ============

ADMIN_KEY = "print3d-admin-2024"


def verify_admin(request):
    """Verify admin authentication.

    Checks both header (X-Admin-Key) and query parameter (key) for flexibility.
    Query parameter is useful for file downloads where headers can't be set.
    """
    admin_key = request.headers.get("X-Admin-Key") or request.args.get("key")
    return admin_key == ADMIN_KEY


@app.route("/api/admin/dashboard")
def admin_dashboard():
    """
    Get admin dashboard summary.

    Returns order counts by status and recent orders.
    """
    if not verify_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    from web.database import get_db_session, count_orders_by_status, list_orders_for_admin

    with get_db_session() as db:
        # Get counts by status
        status_counts = count_orders_by_status(db)

        # Get recent orders that need attention (paid but not shipped)
        pending_production = list_orders_for_admin(db, status="paid", limit=20)
        processing = list_orders_for_admin(db, status="processing", limit=20)

        # Convert to dicts while still in session
        pending_dicts = [o.to_dict() for o in pending_production]
        processing_dicts = [o.to_dict() for o in processing]

    return jsonify({
        "status_counts": status_counts,
        "pending_production": pending_dicts,
        "processing": processing_dicts,
        "timestamp": datetime.utcnow().isoformat(),
    })


@app.route("/api/admin/orders")
def admin_list_orders():
    """
    List orders for admin dashboard.

    Query params:
        - status: Filter by status (paid, processing, shipped, etc.)
        - limit: Max results (default 50)
        - offset: Pagination offset (default 0)
    """
    if not verify_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    from web.database import get_db_session, list_orders_for_admin

    status = request.args.get("status")
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    with get_db_session() as db:
        orders = list_orders_for_admin(db, status=status, limit=limit, offset=offset)

        # Enrich with job info for each order (must be done inside session)
        enriched_orders = []
        for order in orders:
            order_dict = order.to_dict()
            job_id = order.job_id  # Capture before leaving session

            # Get job info to include image/mesh paths
            job = job_service.get_job_status(job_id)
            if job:
                order_dict["job"] = {
                    "description": job.get("description"),
                    "image_url": job.get("image_url"),
                    "mesh_path": job.get("mesh_path"),
                    "status": job.get("status"),
                }

            enriched_orders.append(order_dict)

    return jsonify({
        "orders": enriched_orders,
        "total": len(enriched_orders),
        "limit": limit,
        "offset": offset,
    })


@app.route("/api/admin/orders/<order_id>")
def admin_get_order(order_id: str):
    """
    Get full order details for admin.

    Includes job info and file paths.
    """
    if not verify_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    order = order_service.get_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    order_dict = order.to_dict()

    # Get full job info
    job = job_service.get_job_status(order.job_id)
    if job:
        order_dict["job"] = job

        # Add download URLs
        if job.get("mesh_path"):
            mesh_filename = Path(job["mesh_path"]).name
            order_dict["download_urls"] = {
                "mesh": f"/api/admin/download/{order_id}/mesh",
                "mesh_filename": mesh_filename,
            }
        if job.get("image_url"):
            order_dict["download_urls"] = order_dict.get("download_urls", {})
            order_dict["download_urls"]["image"] = job["image_url"]

    return jsonify(order_dict)


@app.route("/api/admin/download/<order_id>/mesh")
def admin_download_mesh(order_id: str):
    """
    Download mesh file (.glb) for an order.

    Used by admin to manually upload to Craftcloud/TRIDEO.
    """
    if not verify_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    order = order_service.get_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    job = job_service.get_job_status(order.job_id)
    if not job or not job.get("mesh_path"):
        return jsonify({"error": "No mesh file available for this order"}), 404

    mesh_path = resolve_mesh_path(job["mesh_path"])

    if not mesh_path.exists():
        return jsonify({"error": f"Mesh file not found: {mesh_path}"}), 404

    # Send file with descriptive name
    download_name = f"order_{order_id}_{mesh_path.name}"
    return send_file(
        mesh_path,
        as_attachment=True,
        download_name=download_name,
        mimetype="model/gltf-binary",
    )


@app.route("/api/admin/orders/<order_id>/external", methods=["PATCH"])
def admin_update_external_order(order_id: str):
    """
    Update order with external provider info.

    Request body:
        - external_provider: Provider name (craftcloud, trideo, sculpteo, shapeways)
        - external_order_id: Order ID in external system
        - production_cost_usd: Actual production cost
        - shipping_cost_usd: Actual shipping cost
        - admin_notes: Internal notes
    """
    if not verify_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    order = order_service.get_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    from web.database import get_db_session, update_order

    with get_db_session() as db:
        update_fields = {}

        if "external_provider" in data:
            update_fields["external_provider"] = data["external_provider"]
        if "external_order_id" in data:
            update_fields["external_order_id"] = data["external_order_id"]
        if "production_cost_usd" in data:
            update_fields["production_cost_usd"] = float(data["production_cost_usd"])
        if "shipping_cost_usd" in data:
            update_fields["shipping_cost_usd"] = float(data["shipping_cost_usd"])
        if "admin_notes" in data:
            update_fields["admin_notes"] = data["admin_notes"]

        # If external order is set, update status to processing
        if "external_order_id" in data and data["external_order_id"]:
            update_fields["status"] = "processing"

        updated = update_order(db, order_id, **update_fields)

        if not updated:
            return jsonify({"error": "Failed to update order"}), 500

        return jsonify({
            "success": True,
            "order": updated.to_dict(),
        })


@app.route("/api/admin/orders/<order_id>/tracking", methods=["PATCH"])
def admin_update_tracking(order_id: str):
    """
    Update order with tracking info and notify customer.

    Request body:
        - tracking_number: Tracking number from carrier
        - tracking_url: Optional tracking URL
        - notify_customer: Whether to send email notification (default: true)
    """
    if not verify_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    order = order_service.get_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    tracking_number = data.get("tracking_number")
    if not tracking_number:
        return jsonify({"error": "tracking_number is required"}), 400

    tracking_url = data.get("tracking_url", "")
    notify_customer = data.get("notify_customer", True)

    from web.database import get_db_session, update_order

    with get_db_session() as db:
        updated = update_order(
            db, order_id,
            tracking_number=tracking_number,
            tracking_url=tracking_url,
            status="shipped",
        )

        if not updated:
            return jsonify({"error": "Failed to update order"}), 500

    result = {
        "success": True,
        "order_id": order_id,
        "tracking_number": tracking_number,
        "status": "shipped",
    }

    # Send notification email
    if notify_customer and email_service.is_available:
        try:
            email_result = email_service.send_shipping_notification(
                to_email=order.customer_email,
                order_id=order_id,
                tracking_number=tracking_number,
                tracking_url=tracking_url,
            )
            result["email_sent"] = email_result.success
            if not email_result.success:
                result["email_error"] = email_result.error
        except Exception as e:
            result["email_sent"] = False
            result["email_error"] = str(e)
    else:
        result["email_sent"] = False
        result["email_error"] = "Email service not available" if notify_customer else "Notification disabled"

    return jsonify(result)


@app.route("/api/admin/orders/<order_id>/status", methods=["PATCH"])
def admin_update_status(order_id: str):
    """
    Update order status.

    Request body:
        - status: New status (paid, processing, shipped, delivered, cancelled)
    """
    if not verify_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    order = order_service.get_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    data = request.get_json()
    if not data or "status" not in data:
        return jsonify({"error": "status is required"}), 400

    valid_statuses = ["pending", "paid", "processing", "shipped", "delivered", "cancelled", "refunded"]
    new_status = data["status"]

    if new_status not in valid_statuses:
        return jsonify({
            "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        }), 400

    from web.database import get_db_session, update_order

    with get_db_session() as db:
        updated = update_order(db, order_id, status=new_status)

        if not updated:
            return jsonify({"error": "Failed to update order"}), 500

        return jsonify({
            "success": True,
            "order_id": order_id,
            "status": new_status,
        })


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

@app.route("/admin")
def serve_admin_dashboard():
    """Serve admin dashboard HTML."""
    static_dir = Path(__file__).parent / "static"
    return send_from_directory(static_dir, "admin.html")


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
