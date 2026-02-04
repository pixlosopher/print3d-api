#!/usr/bin/env python3
"""
Simple web demo for the 3D pipeline
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime
import http.server
import socketserver
import urllib.parse
import cgi
import io
import base64

class PipelineWebHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_demo_page()
        elif self.path.startswith('/output/'):
            # Serve output files
            super().do_GET()
        elif self.path == '/status':
            self.send_json_response({"status": "ready", "timestamp": datetime.now().isoformat()})
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path == '/generate':
            self.handle_generation()
        else:
            self.send_error(404)
    
    def send_demo_page(self):
        """Send the demo HTML page"""
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Pipeline Demo</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { background: #f5f5f5; padding: 20px; border-radius: 10px; }
        .input-group { margin-bottom: 15px; }
        label { display: block; font-weight: bold; margin-bottom: 5px; }
        input[type="text"], select { width: 100%; padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px; }
        button { background: #007bff; color: white; padding: 12px 24px; font-size: 16px; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .results { margin-top: 20px; padding: 15px; background: white; border-radius: 5px; }
        .loading { display: none; color: #007bff; }
        .error { color: #dc3545; }
        .success { color: #28a745; }
        .file-link { display: inline-block; margin: 5px; padding: 8px 16px; background: #28a745; color: white; text-decoration: none; border-radius: 3px; }
        .file-link:hover { background: #1e7e34; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 3D Pipeline Demo</h1>
        <p>Generate images and 3D models from text descriptions!</p>
        
        <form id="generateForm">
            <div class="input-group">
                <label for="prompt">What do you want to create?</label>
                <input type="text" id="prompt" name="prompt" placeholder="e.g., cute robot with hat" required>
            </div>
            
            <div class="input-group">
                <label for="style">Style:</label>
                <select id="style" name="style">
                    <option value="figurine">Figurine</option>
                    <option value="character">Character</option>
                    <option value="sculpture">Sculpture</option>
                    <option value="object">Object</option>
                    <option value="miniature">Miniature</option>
                </select>
            </div>
            
            <div class="input-group">
                <label for="size">Size (mm):</label>
                <select id="size" name="size">
                    <option value="30">30mm (Small)</option>
                    <option value="50" selected>50mm (Medium)</option>
                    <option value="75">75mm (Large)</option>
                    <option value="100">100mm (Extra Large)</option>
                </select>
            </div>
            
            <button type="submit" id="generateBtn">🚀 Generate 3D Model</button>
        </form>
        
        <div class="loading" id="loading">
            <p>🔄 Generating your 3D model... This may take 30-60 seconds.</p>
        </div>
        
        <div class="results" id="results" style="display: none;">
            <h3>Results:</h3>
            <div id="resultContent"></div>
        </div>
    </div>

    <script>
        document.getElementById('generateForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            
            // Show loading
            document.getElementById('generateBtn').disabled = true;
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showResults(result);
                } else {
                    showError(result.error || 'Unknown error');
                }
            } catch (error) {
                showError('Network error: ' + error.message);
            } finally {
                document.getElementById('generateBtn').disabled = false;
                document.getElementById('loading').style.display = 'none';
            }
        });
        
        function showResults(result) {
            const resultsDiv = document.getElementById('results');
            const contentDiv = document.getElementById('resultContent');
            
            let html = '<div class="success">✅ Generation complete!</div>';
            html += '<p><strong>⏱️ Total time:</strong> ' + result.total_time + 's</p>';
            
            if (result.image_path) {
                html += '<p><strong>🖼️ Generated Image:</strong></p>';
                html += '<img src="' + result.image_path + '" style="max-width: 400px; border-radius: 5px;">';
                html += '<br><a href="' + result.image_path + '" class="file-link" download>📥 Download Image</a>';
            }
            
            if (result.mesh_path) {
                html += '<p><strong>🧊 3D Mesh:</strong></p>';
                html += '<p>📊 ' + result.vertices + ' vertices, ' + result.faces + ' faces</p>';
                html += '<a href="' + result.mesh_path + '" class="file-link" download>📥 Download 3D Model (.obj)</a>';
            }
            
            if (result.pricing) {
                html += '<p><strong>💰 Estimated Print Costs:</strong></p>';
                html += '<ul>';
                for (const [material, info] of Object.entries(result.pricing)) {
                    html += '<li>' + material + ': $' + info.price + ' (' + info.shipping + ' days)</li>';
                }
                html += '</ul>';
            }
            
            contentDiv.innerHTML = html;
            resultsDiv.style.display = 'block';
        }
        
        function showError(error) {
            const resultsDiv = document.getElementById('results');
            const contentDiv = document.getElementById('resultContent');
            
            contentDiv.innerHTML = '<div class="error">❌ Error: ' + error + '</div>';
            resultsDiv.style.display = 'block';
        }
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def handle_generation(self):
        """Handle 3D generation request"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            prompt = data.get('prompt', 'cube')
            style = data.get('style', 'figurine')
            size = float(data.get('size', 50))
            
            print(f"🚀 Web request: {prompt} ({style}, {size}mm)")
            
            # Run the pipeline
            result = self.run_pipeline(prompt, style, size)
            
            self.send_json_response(result)
            
        except Exception as e:
            print(f"❌ Generation error: {e}")
            self.send_json_response({"success": False, "error": str(e)})
    
    def run_pipeline(self, prompt, style, size):
        """Run the 3D pipeline"""
        try:
            # Use the working pipeline
            cmd = [
                'python3', 'final_pipeline.py', 
                prompt,
                '--style', style,
                '--size', str(size),
                '--material', 'balanced'
            ]
            
            print(f"🔄 Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd='.')
            
            if result.returncode == 0:
                # Look for the results JSON file
                output_dir = Path('output')
                json_files = list(output_dir.glob('pipeline_complete_*.json'))
                
                if json_files:
                    latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
                    
                    with open(latest_file) as f:
                        pipeline_result = json.load(f)
                    
                    return {
                        "success": True,
                        "total_time": pipeline_result.get("total_pipeline_time", 0),
                        "image_path": pipeline_result["image"]["file_path"],
                        "mesh_path": pipeline_result["mesh"]["file_path"], 
                        "vertices": pipeline_result["mesh"]["vertices"],
                        "faces": pipeline_result["mesh"]["faces"],
                        "pricing": pipeline_result["cost_analysis"]["all_material_options"]
                    }
                else:
                    return {"success": False, "error": "No result file found"}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Generation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_json_response(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

def start_web_demo(port=8080):
    """Start the web demo server"""
    
    # Change to print3d directory
    import os
    os.chdir(Path(__file__).parent)
    
    print(f"🌐 Starting 3D Pipeline Web Demo")
    print(f"📡 Server: http://localhost:{port}")
    print(f"📁 Directory: {Path.cwd()}")
    print(f"🎯 Ready to generate 3D models!")
    print(f"\n🔗 Copy this link: http://localhost:{port}")
    
    with socketserver.TCPServer(("", port), PipelineWebHandler) as httpd:
        print(f"🚀 Server running on port {port}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print(f"\n⏹️ Server stopped")

if __name__ == "__main__":
    start_web_demo()