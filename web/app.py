#!/usr/bin/env python3
"""
Web preview interface for 3D Print Pipeline
Run with: python app.py
Access at: http://localhost:8888
"""

from flask import Flask, render_template, request, jsonify
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__, template_folder='templates', static_folder='static')

# Pipeline status tracking
pipeline_status = {
    "step": None,
    "progress": 0,
    "image_url": None,
    "mesh_url": None,
    "pricing": None,
    "error": None
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def status():
    """Check if API keys are configured"""
    from config import get_config
    try:
        config = get_config()
        return jsonify({
            "meshy": bool(config.meshy_api_key),
            "shapeways": bool(config.shapeways_client_id),
            "fal": bool(config.fal_key),
            "gemini": bool(config.gemini_api_key),
        })
    except Exception as e:
        return jsonify({"error": str(e), "meshy": False, "shapeways": False, "fal": False, "gemini": False})

@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    """Generate 2D image from prompt"""
    data = request.json
    prompt = data.get('prompt', '')
    
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    
    try:
        from image_gen import ImageGenerator
        generator = ImageGenerator()
        result = generator.generate(prompt)
        return jsonify({
            "success": True,
            "image_url": result.url,
            "local_path": result.local_path
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/convert-to-3d', methods=['POST'])
def convert_to_3d():
    """Convert image to 3D model"""
    data = request.json
    image_url = data.get('image_url', '')
    
    if not image_url:
        return jsonify({"error": "No image URL provided"}), 400
    
    try:
        from mesh_gen import MeshGenerator
        generator = MeshGenerator()
        result = generator.from_image(image_url)
        return jsonify({
            "success": True,
            "task_id": result.task_id,
            "status": result.status,
            "model_url": result.model_url,
            "preview_url": result.preview_url
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mesh-status/<task_id>')
def mesh_status(task_id):
    """Check status of 3D conversion"""
    try:
        from mesh_gen import MeshGenerator
        generator = MeshGenerator()
        result = generator.check_status(task_id)
        return jsonify({
            "success": True,
            "status": result.status,
            "progress": result.progress,
            "model_url": result.model_url,
            "preview_url": result.preview_url
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pricing', methods=['POST'])
def get_pricing():
    """Get 3D printing pricing"""
    data = request.json
    model_path = data.get('model_path', '')
    
    try:
        from print_api import PrintService
        service = PrintService()
        # This would normally upload and get pricing
        # For preview, return mock data
        return jsonify({
            "success": True,
            "materials": [
                {"name": "White Plastic (SLS)", "price": 12.50, "currency": "USD"},
                {"name": "Black Plastic (MJF)", "price": 15.00, "currency": "USD"},
                {"name": "Stainless Steel", "price": 45.00, "currency": "USD"},
                {"name": "Full Color Sandstone", "price": 22.00, "currency": "USD"}
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/demo')
def demo_mode():
    """Return demo data for preview without API keys"""
    return jsonify({
        "demo": True,
        "sample_prompts": [
            "a cute robot with big friendly eyes, figurine style",
            "a geometric owl sculpture, low poly art",
            "a miniature spaceship, sci-fi design",
            "a chess piece - knight, medieval style"
        ],
        "sample_image": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=512",
        "sample_3d_preview": "https://sketchfab.com/models/faef9fe5ace445e7b2989d1c1eda691c/embed"
    })

if __name__ == '__main__':
    print("🖨️  3D Print Pipeline Preview")
    print("   Open http://localhost:8888 in your browser")
    app.run(host='127.0.0.1', port=8888, debug=True)
