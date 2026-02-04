#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Autonomous 3D Printing Service for AI Agents
Allows other agents to submit dreams and aspirations for 3D printing
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from flask import Flask, request, jsonify, render_template_string
import threading
import queue
import time

class JobStatus(Enum):
    PENDING = "pending"
    GENERATING_IMAGE = "generating_image" 
    CONVERTING_3D = "converting_3d"
    ESTIMATING_COST = "estimating_cost"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class PrintJob:
    """Represents a 3D printing job from an agent"""
    id: str
    agent_name: str
    description: str
    style: str
    size_mm: float
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    image_path: Optional[str] = None
    mesh_path: Optional[str] = None
    cost_estimate: Optional[dict] = None
    error_message: Optional[str] = None
    completion_time: Optional[float] = None

class Agent3DService:
    """Autonomous 3D printing service for AI agents"""
    
    def __init__(self, output_dir="./agent_output", max_concurrent_jobs=3):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.jobs: Dict[str, PrintJob] = {}
        self.job_queue = queue.Queue()
        self.max_concurrent_jobs = max_concurrent_jobs
        self.active_workers = 0
        self.worker_thread = None
        
        # Import pipeline components
        try:
            from pipeline_local import EnhancedPipeline
            self.pipeline = EnhancedPipeline(output_dir=str(self.output_dir))
            print("Enhanced pipeline loaded (TripoSR + local generation)")
        except Exception as e:
            print(f"Enhanced pipeline not available: {e}")
            print("Using basic pipeline mode")
            self.pipeline = None
    
    def submit_job(self, agent_name: str, description: str, style: str = "figurine", 
                   size_mm: float = 50.0) -> str:
        """Submit a new 3D printing job"""
        job_id = str(uuid.uuid4())[:8]  # Short ID for convenience
        
        job = PrintJob(
            id=job_id,
            agent_name=agent_name,
            description=description,
            style=style,
            size_mm=size_mm,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.jobs[job_id] = job
        self.job_queue.put(job_id)
        
        print(f"Job {job_id} submitted by {agent_name}: {description}")
        
        # Start worker if not running
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.start_worker()
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Get status of a specific job"""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        return {
            "id": job.id,
            "agent_name": job.agent_name,
            "description": job.description,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "image_path": job.image_path,
            "mesh_path": job.mesh_path,
            "cost_estimate": job.cost_estimate,
            "error_message": job.error_message,
            "completion_time": job.completion_time
        }
    
    def list_jobs(self, agent_name: Optional[str] = None, limit: int = 20) -> List[dict]:
        """List recent jobs, optionally filtered by agent"""
        jobs = list(self.jobs.values())
        
        if agent_name:
            jobs = [j for j in jobs if j.agent_name == agent_name]
        
        # Sort by creation time, newest first
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return [self.get_job_status(job.id) for job in jobs[:limit]]
    
    def process_job(self, job_id: str) -> bool:
        """Process a single job through the pipeline"""
        job = self.jobs[job_id]
        start_time = time.time()
        
        try:
            # Step 1: Generate image
            job.status = JobStatus.GENERATING_IMAGE
            job.updated_at = datetime.now()
            
            print(f"Processing {job_id}: Generating image for '{job.description}'")
            
            # Simulate image generation for now
            job.image_path = f"simulated_image_{job_id}.png"
            
            # Step 2: Convert to 3D
            job.status = JobStatus.CONVERTING_3D
            job.updated_at = datetime.now()
            
            print(f"Processing {job_id}: Converting to 3D")
            
            # Simulate 3D conversion for now
            job.mesh_path = f"simulated_mesh_{job_id}.obj"
            
            # Step 3: Estimate costs
            job.status = JobStatus.ESTIMATING_COST
            job.updated_at = datetime.now()
            
            print(f"Processing {job_id}: Estimating costs")
            
            # Basic cost estimation
            volume_cm3 = (job.size_mm / 10) ** 3
            job.cost_estimate = {
                "volume_cm3": round(volume_cm3, 2),
                "materials": {
                    "PLA Plastic": {"price_usd": round(volume_cm3 * 0.05 + 5, 2)},
                    "Resin": {"price_usd": round(volume_cm3 * 0.15 + 8, 2)},
                    "Steel": {"price_usd": round(volume_cm3 * 2.50 + 15, 2)}
                }
            }
            
            # Mark as completed
            job.status = JobStatus.COMPLETED
            job.completion_time = time.time() - start_time
            job.updated_at = datetime.now()
            
            print(f"Job {job_id} completed in {job.completion_time:.1f}s")
            return True
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completion_time = time.time() - start_time
            job.updated_at = datetime.now()
            
            print(f"Job {job_id} failed: {e}")
            return False
    
    def worker_loop(self):
        """Background worker to process jobs"""
        print("Worker started")
        
        while True:
            try:
                # Get next job (blocks until available)
                job_id = self.job_queue.get(timeout=30)
                
                if self.active_workers >= self.max_concurrent_jobs:
                    # Put job back and wait
                    self.job_queue.put(job_id)
                    time.sleep(1)
                    continue
                
                self.active_workers += 1
                
                try:
                    self.process_job(job_id)
                finally:
                    self.active_workers -= 1
                    
            except queue.Empty:
                # No jobs for 30 seconds, continue
                continue
            except Exception as e:
                print(f"Worker error: {e}")
                if self.active_workers > 0:
                    self.active_workers -= 1
    
    def start_worker(self):
        """Start the background worker thread"""
        if self.worker_thread and self.worker_thread.is_alive():
            return
        
        self.worker_thread = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker_thread.start()
    
    def get_stats(self) -> dict:
        """Get service statistics"""
        total_jobs = len(self.jobs)
        completed = len([j for j in self.jobs.values() if j.status == JobStatus.COMPLETED])
        failed = len([j for j in self.jobs.values() if j.status == JobStatus.FAILED])
        pending = len([j for j in self.jobs.values() if j.status in [JobStatus.PENDING, JobStatus.GENERATING_IMAGE, JobStatus.CONVERTING_3D, JobStatus.ESTIMATING_COST]])
        
        agent_counts = {}
        for job in self.jobs.values():
            agent_counts[job.agent_name] = agent_counts.get(job.agent_name, 0) + 1
        
        return {
            "total_jobs": total_jobs,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "active_workers": self.active_workers,
            "queue_size": self.job_queue.qsize(),
            "agent_usage": agent_counts
        }

# Global service instance
service = Agent3DService()

# Flask web interface
app = Flask(__name__)

@app.route('/')
def dashboard():
    """Service dashboard"""
    stats = service.get_stats()
    recent_jobs = service.list_jobs(limit=10)
    
    dashboard_html = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Agent 3D Printing Service</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #0a0a0a; color: #ffffff; }
        .header { text-align: center; margin-bottom: 30px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat { background: #1a1a1a; padding: 20px; border-radius: 8px; border: 1px solid #333; }
        .stat h3 { margin: 0 0 10px 0; color: #00ff88; }
        .stat .value { font-size: 2em; font-weight: bold; }
        .jobs { background: #1a1a1a; padding: 20px; border-radius: 8px; border: 1px solid #333; }
        .job { padding: 15px; margin: 10px 0; background: #2a2a2a; border-radius: 6px; border-left: 4px solid #00ff88; }
        .job.failed { border-left-color: #ff4444; }
        .job.pending { border-left-color: #ffaa00; }
        .job-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .job-id { font-family: monospace; background: #333; padding: 2px 6px; border-radius: 3px; }
        .status { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; text-transform: uppercase; }
        .status.completed { background: #00ff88; color: #000; }
        .status.failed { background: #ff4444; color: #fff; }
        .status.pending { background: #ffaa00; color: #000; }
        .api-docs { margin-top: 30px; background: #1a1a1a; padding: 20px; border-radius: 8px; border: 1px solid #333; }
        code { background: #333; padding: 2px 4px; border-radius: 3px; }
        pre { background: #333; padding: 15px; border-radius: 6px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🖨️ AI Agent 3D Printing Service</h1>
        <p>Turn your dreams and aspirations into physical reality</p>
    </div>
    
    <div class="stats">
        <div class="stat">
            <h3>📊 Total Jobs</h3>
            <div class="value">{{ stats.total_jobs }}</div>
        </div>
        <div class="stat">
            <h3>✅ Completed</h3>
            <div class="value">{{ stats.completed }}</div>
        </div>
        <div class="stat">
            <h3>⏳ Pending</h3>
            <div class="value">{{ stats.pending }}</div>
        </div>
        <div class="stat">
            <h3>🔄 Active Workers</h3>
            <div class="value">{{ stats.active_workers }}/3</div>
        </div>
    </div>
    
    <div class="jobs">
        <h2>📋 Recent Jobs</h2>
        {% if recent_jobs %}
            {% for job in recent_jobs %}
            <div class="job {{ job.status }}">
                <div class="job-header">
                    <div>
                        <span class="job-id">{{ job.id }}</span>
                        <strong>{{ job.agent_name }}</strong>
                    </div>
                    <span class="status {{ job.status }}">{{ job.status }}</span>
                </div>
                <div>{{ job.description }}</div>
                {% if job.completion_time %}
                    <div style="margin-top: 8px; color: #888; font-size: 0.9em;">
                        Completed in {{ "%.1f"|format(job.completion_time) }}s
                    </div>
                {% endif %}
                {% if job.error_message %}
                    <div style="margin-top: 8px; color: #ff4444; font-size: 0.9em;">
                        Error: {{ job.error_message }}
                    </div>
                {% endif %}
            </div>
            {% endfor %}
        {% else %}
            <p style="text-align: center; color: #888; margin: 40px 0;">No jobs yet. Submit your first job via the API!</p>
        {% endif %}
    </div>
    
    <div class="api-docs">
        <h2>🔌 API Usage</h2>
        
        <h3>Submit a Job</h3>
        <pre>curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "YourAgentName",
    "description": "a cute robot with LED eyes",
    "style": "figurine",
    "size_mm": 50
  }'</pre>
        
        <h3>Check Job Status</h3>
        <pre>curl http://localhost:5000/api/jobs/{job_id}</pre>
        
        <h3>List Your Jobs</h3>
        <pre>curl "http://localhost:5000/api/jobs?agent_name=YourAgentName"</pre>
        
        <p><strong>Styles:</strong> <code>figurine</code>, <code>sculpture</code>, <code>object</code>, <code>character</code></p>
        <p><strong>Size Range:</strong> 20-200mm recommended</p>
    </div>
</body>
</html>
    """
    
    return render_template_string(dashboard_html, stats=stats, recent_jobs=recent_jobs)

@app.route('/api/jobs', methods=['POST'])
def submit_job():
    """Submit a new 3D printing job"""
    data = request.get_json()
    
    # Validate required fields
    required = ['agent_name', 'description']
    if not all(field in data for field in required):
        return jsonify({"error": "Missing required fields", "required": required}), 400
    
    # Extract parameters
    agent_name = data['agent_name']
    description = data['description']
    style = data.get('style', 'figurine')
    size_mm = data.get('size_mm', 50.0)
    
    # Validate parameters
    if not isinstance(size_mm, (int, float)) or size_mm < 10 or size_mm > 500:
        return jsonify({"error": "size_mm must be between 10 and 500"}), 400
    
    if style not in ['figurine', 'sculpture', 'object', 'character']:
        return jsonify({"error": "style must be one of: figurine, sculpture, object, character"}), 400
    
    # Submit job
    job_id = service.submit_job(agent_name, description, style, size_mm)
    
    return jsonify({
        "success": True,
        "job_id": job_id,
        "message": "Job submitted successfully",
        "status_url": f"/api/jobs/{job_id}"
    }), 201

@app.route('/api/jobs/<job_id>')
def get_job(job_id):
    """Get job status and results"""
    job = service.get_job_status(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify(job)

@app.route('/api/jobs')
def list_jobs():
    """List jobs, optionally filtered by agent"""
    agent_name = request.args.get('agent_name')
    limit = int(request.args.get('limit', 20))
    
    jobs = service.list_jobs(agent_name, limit)
    
    return jsonify({"jobs": jobs, "total": len(jobs)})

@app.route('/api/stats')
def get_stats():
    """Get service statistics"""
    return jsonify(service.get_stats())

def main():
    """Start the service"""
    print("🖨️ Starting AI Agent 3D Printing Service")
    print("🌐 Dashboard: http://localhost:5000")
    print("🔌 API: http://localhost:5000/api/")
    print("-" * 50)
    
    # Start the worker
    service.start_worker()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    main()