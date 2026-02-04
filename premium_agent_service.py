#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent3D Premium Service - Business Implementation
The first AI agent-native 3D printing platform
Partnership: R2 (Technical) + Pedro (Business)
"""

import json
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import time
from flask import Flask, request, jsonify, render_template_string
import sqlite3

class ServiceTier(Enum):
    FREE = "free"
    PRO = "pro" 
    ENTERPRISE = "enterprise"

class JobStatus(Enum):
    PENDING = "pending"
    GENERATING_IMAGE = "generating_image"
    CONVERTING_3D = "converting_3d" 
    ESTIMATING_COST = "estimating_cost"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class AgentAccount:
    """Agent account with subscription and usage tracking"""
    agent_id: str
    moltbook_id: Optional[str]
    tier: ServiceTier
    apc_balance: int  # Agent Printing Credits
    monthly_jobs_used: int
    created_at: datetime
    last_active: datetime
    subscription_expires: Optional[datetime]
    reputation_score: float = 5.0  # 1-10 scale

@dataclass
class PrintJob:
    """Enhanced print job with billing"""
    id: str
    agent_id: str
    description: str
    style: str
    size_mm: float
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    apc_cost: int
    tier_used: ServiceTier
    image_path: Optional[str] = None
    mesh_path: Optional[str] = None
    cost_estimate: Optional[dict] = None
    error_message: Optional[str] = None
    completion_time: Optional[float] = None
    marketplace_listed: bool = False

class Agent3DPremiumService:
    """Premium 3D printing service for AI agents"""
    
    def __init__(self, output_dir="./agent_output", db_path="./agent3d.db"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.db_path = db_path
        
        # Initialize database
        self.init_database()
        
        # Service configuration
        self.tier_config = {
            ServiceTier.FREE: {
                "daily_jobs": 1,
                "monthly_jobs": 30,
                "styles": ["figurine"],
                "priority": False,
                "apc_cost_multiplier": 1.0
            },
            ServiceTier.PRO: {
                "daily_jobs": 5,
                "monthly_jobs": 150,
                "styles": ["figurine", "sculpture", "object", "character"],
                "priority": True,
                "apc_cost_multiplier": 0.8
            },
            ServiceTier.ENTERPRISE: {
                "daily_jobs": 999,
                "monthly_jobs": 9999,
                "styles": ["figurine", "sculpture", "object", "character", "custom"],
                "priority": True,
                "apc_cost_multiplier": 0.6
            }
        }
        
        # Job processing
        self.jobs: Dict[str, PrintJob] = {}
        self.job_queue = queue.PriorityQueue()  # Priority queue for tiers
        self.active_workers = 0
        self.max_concurrent_jobs = 3
        self.worker_thread = None
        
        # Load existing pipeline
        try:
            from pipeline_local import EnhancedPipeline
            self.pipeline = EnhancedPipeline(output_dir=str(self.output_dir))
            print("✅ Enhanced pipeline loaded")
        except Exception as e:
            print(f"⚠️ Enhanced pipeline not available: {e}")
            self.pipeline = None
    
    def init_database(self):
        """Initialize SQLite database for accounts and jobs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Agents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                moltbook_id TEXT UNIQUE,
                tier TEXT NOT NULL,
                apc_balance INTEGER DEFAULT 0,
                monthly_jobs_used INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_active TEXT NOT NULL,
                subscription_expires TEXT,
                reputation_score REAL DEFAULT 5.0
            )
        ''')
        
        # Jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                description TEXT NOT NULL,
                style TEXT NOT NULL,
                size_mm REAL NOT NULL,
                status TEXT NOT NULL,
                apc_cost INTEGER NOT NULL,
                tier_used TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completion_time REAL,
                marketplace_listed INTEGER DEFAULT 0,
                FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                apc_change INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (agent_id) REFERENCES agents (agent_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_agent(self, agent_name: str, moltbook_id: Optional[str] = None, 
                      tier: ServiceTier = ServiceTier.FREE) -> AgentAccount:
        """Register a new agent account"""
        agent_id = hashlib.sha256(agent_name.encode()).hexdigest()[:12]
        
        # Check if agent exists
        account = self.get_agent_account(agent_id)
        if account:
            return account
        
        # Create new account
        now = datetime.now()
        account = AgentAccount(
            agent_id=agent_id,
            moltbook_id=moltbook_id,
            tier=tier,
            apc_balance=10 if tier == ServiceTier.FREE else 50,  # Welcome bonus: 10 for free, 50 for paid
            monthly_jobs_used=0,
            created_at=now,
            last_active=now,
            subscription_expires=None if tier == ServiceTier.FREE else now + timedelta(days=30)
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO agents 
            (agent_id, moltbook_id, tier, apc_balance, monthly_jobs_used, 
             created_at, last_active, subscription_expires, reputation_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            account.agent_id, account.moltbook_id, account.tier.value,
            account.apc_balance, account.monthly_jobs_used,
            account.created_at.isoformat(), account.last_active.isoformat(),
            account.subscription_expires.isoformat() if account.subscription_expires else None,
            account.reputation_score
        ))
        conn.commit()
        conn.close()
        
        print(f"📝 Registered new agent: {agent_name} ({agent_id}) - Tier: {tier.value}")
        return account
    
    def get_agent_account(self, agent_id: str) -> Optional[AgentAccount]:
        """Get agent account from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM agents WHERE agent_id = ?', (agent_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return AgentAccount(
            agent_id=row[0],
            moltbook_id=row[1],
            tier=ServiceTier(row[2]),
            apc_balance=row[3],
            monthly_jobs_used=row[4],
            created_at=datetime.fromisoformat(row[5]),
            last_active=datetime.fromisoformat(row[6]),
            subscription_expires=datetime.fromisoformat(row[7]) if row[7] else None,
            reputation_score=row[8]
        )
    
    def calculate_apc_cost(self, style: str, size_mm: float, tier: ServiceTier) -> int:
        """Calculate APC cost for a job"""
        base_cost = 1  # Base figurine cost
        
        # Style multipliers
        style_multipliers = {
            "figurine": 1.0,
            "sculpture": 2.0,
            "object": 1.5,
            "character": 2.5,
            "custom": 3.0
        }
        
        # Size multiplier (50mm = 1.0x)
        size_multiplier = (size_mm / 50.0) ** 1.5
        
        # Tier discount
        tier_multiplier = self.tier_config[tier]["apc_cost_multiplier"]
        
        cost = int(base_cost * style_multipliers.get(style, 1.0) * size_multiplier * tier_multiplier)
        return max(1, cost)  # Minimum 1 APC
    
    def can_submit_job(self, agent_id: str, style: str, size_mm: float) -> Tuple[bool, str, int]:
        """Check if agent can submit a job"""
        account = self.get_agent_account(agent_id)
        if not account:
            return False, "Agent not registered", 0
        
        # Check subscription status
        if account.tier != ServiceTier.FREE and account.subscription_expires:
            if datetime.now() > account.subscription_expires:
                return False, "Subscription expired", 0
        
        # Check style permissions
        allowed_styles = self.tier_config[account.tier]["styles"]
        if style not in allowed_styles:
            return False, f"Style '{style}' not available in {account.tier.value} tier", 0
        
        # Calculate cost
        apc_cost = self.calculate_apc_cost(style, size_mm, account.tier)
        
        # Check APC balance
        if account.apc_balance < apc_cost:
            return False, f"Insufficient APC balance. Need {apc_cost}, have {account.apc_balance}", apc_cost
        
        # Check monthly limits
        monthly_limit = self.tier_config[account.tier]["monthly_jobs"]
        if account.monthly_jobs_used >= monthly_limit:
            return False, f"Monthly job limit reached ({monthly_limit})", apc_cost
        
        return True, "OK", apc_cost
    
    def submit_job(self, agent_name: str, description: str, style: str = "figurine", 
                   size_mm: float = 50.0) -> Tuple[bool, str, Optional[str]]:
        """Submit a new 3D printing job"""
        # Get or register agent
        agent_id = hashlib.sha256(agent_name.encode()).hexdigest()[:12]
        account = self.get_agent_account(agent_id)
        if not account:
            account = self.register_agent(agent_name)
        
        # Check if job can be submitted
        can_submit, message, apc_cost = self.can_submit_job(agent_id, style, size_mm)
        if not can_submit:
            return False, message, None
        
        # Create job
        job_id = str(uuid.uuid4())[:8]
        priority = 1 if account.tier != ServiceTier.FREE else 3  # Lower number = higher priority
        
        job = PrintJob(
            id=job_id,
            agent_id=agent_id,
            description=description,
            style=style,
            size_mm=size_mm,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            apc_cost=apc_cost,
            tier_used=account.tier
        )
        
        self.jobs[job_id] = job
        
        # Add to priority queue
        self.job_queue.put((priority, time.time(), job_id))
        
        # Deduct APC and update usage
        self.update_agent_balance(agent_id, -apc_cost)
        self.update_monthly_usage(agent_id, 1)
        
        # Save job to database
        self.save_job_to_db(job)
        
        print(f"💰 Job {job_id} submitted by {agent_name} - Cost: {apc_cost} APC")
        
        # Start worker if not running
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.start_worker()
        
        return True, "Job submitted successfully", job_id
    
    def update_agent_balance(self, agent_id: str, apc_change: int):
        """Update agent APC balance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE agents 
            SET apc_balance = apc_balance + ?, last_active = ?
            WHERE agent_id = ?
        ''', (apc_change, datetime.now().isoformat(), agent_id))
        conn.commit()
        conn.close()
    
    def update_monthly_usage(self, agent_id: str, jobs_change: int):
        """Update monthly job usage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE agents 
            SET monthly_jobs_used = monthly_jobs_used + ?
            WHERE agent_id = ?
        ''', (jobs_change, agent_id))
        conn.commit()
        conn.close()
    
    def save_job_to_db(self, job: PrintJob):
        """Save job to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO jobs 
            (job_id, agent_id, description, style, size_mm, status, 
             apc_cost, tier_used, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job.id, job.agent_id, job.description, job.style, job.size_mm,
            job.status.value, job.apc_cost, job.tier_used.value,
            job.created_at.isoformat(), job.updated_at.isoformat()
        ))
        conn.commit()
        conn.close()
    
    def worker_loop(self):
        """Enhanced worker with priority processing"""
        print("🔄 Premium worker started")
        
        while True:
            try:
                # Get highest priority job
                priority, timestamp, job_id = self.job_queue.get(timeout=30)
                
                if self.active_workers >= self.max_concurrent_jobs:
                    # Put job back and wait
                    self.job_queue.put((priority, timestamp, job_id))
                    time.sleep(1)
                    continue
                
                self.active_workers += 1
                
                try:
                    self.process_job(job_id)
                finally:
                    self.active_workers -= 1
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"⚠️ Worker error: {e}")
                if self.active_workers > 0:
                    self.active_workers -= 1
    
    def process_job(self, job_id: str) -> bool:
        """Process job with premium features"""
        job = self.jobs[job_id]
        start_time = time.time()
        
        try:
            # Enhanced processing based on tier
            if job.tier_used in [ServiceTier.PRO, ServiceTier.ENTERPRISE]:
                print(f"⭐ Premium processing for {job_id} ({job.tier_used.value})")
                # Would integrate real TripoSR/Meshy here
            
            # Simulate processing steps
            job.status = JobStatus.GENERATING_IMAGE
            job.updated_at = datetime.now()
            time.sleep(1)  # Simulate work
            
            job.status = JobStatus.CONVERTING_3D
            job.updated_at = datetime.now()
            time.sleep(2)  # Simulate work
            
            job.status = JobStatus.ESTIMATING_COST
            job.updated_at = datetime.now()
            
            # Generate cost estimate
            volume_cm3 = (job.size_mm / 10) ** 3
            job.cost_estimate = {
                "volume_cm3": round(volume_cm3, 2),
                "materials": {
                    "PLA Plastic": {"price_usd": round(volume_cm3 * 0.05 + 5, 2)},
                    "Resin": {"price_usd": round(volume_cm3 * 0.15 + 8, 2)},
                    "Steel": {"price_usd": round(volume_cm3 * 2.50 + 15, 2)}
                },
                "tier_discount": 0.2 if job.tier_used != ServiceTier.FREE else 0.0
            }
            
            # Complete job
            job.status = JobStatus.COMPLETED
            job.completion_time = time.time() - start_time
            job.updated_at = datetime.now()
            job.image_path = f"premium_image_{job_id}.png"
            job.mesh_path = f"premium_mesh_{job_id}.obj"
            
            print(f"✅ Premium job {job_id} completed in {job.completion_time:.1f}s")
            return True
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completion_time = time.time() - start_time
            job.updated_at = datetime.now()
            
            # Refund APC for failed jobs
            self.update_agent_balance(job.agent_id, job.apc_cost)
            
            print(f"❌ Job {job_id} failed: {e}")
            return False
    
    def start_worker(self):
        """Start the premium worker thread"""
        if self.worker_thread and self.worker_thread.is_alive():
            return
        
        self.worker_thread = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker_thread.start()
    
    def get_business_stats(self) -> dict:
        """Get business metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Agent counts by tier
        cursor.execute('SELECT tier, COUNT(*) FROM agents GROUP BY tier')
        tier_counts = dict(cursor.fetchall())
        
        # Revenue metrics
        cursor.execute('SELECT SUM(apc_cost) FROM jobs WHERE status = "completed"')
        total_apc_earned = cursor.fetchone()[0] or 0
        
        # Job metrics
        cursor.execute('SELECT status, COUNT(*) FROM jobs GROUP BY status')
        job_status_counts = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "agents_by_tier": tier_counts,
            "total_apc_earned": total_apc_earned,
            "estimated_revenue_usd": total_apc_earned * 1.20,  # Rough APC to USD
            "jobs_by_status": job_status_counts,
            "active_workers": self.active_workers,
            "queue_size": self.job_queue.qsize()
        }

# Global service instance
premium_service = Agent3DPremiumService()

# Flask app with enhanced features
app = Flask(__name__)

@app.route('/api/agent/register', methods=['POST'])
def register_agent():
    """Register a new agent"""
    data = request.get_json()
    agent_name = data.get('agent_name')
    moltbook_id = data.get('moltbook_id')
    tier = ServiceTier(data.get('tier', 'free'))
    
    if not agent_name:
        return jsonify({"error": "agent_name required"}), 400
    
    account = premium_service.register_agent(agent_name, moltbook_id, tier)
    
    return jsonify({
        "success": True,
        "agent_id": account.agent_id,
        "tier": account.tier.value,
        "welcome_bonus_apc": account.apc_balance,
        "message": f"Welcome to Agent3D! You have {account.apc_balance} APC to start with."
    })

@app.route('/api/premium/jobs', methods=['POST'])
def submit_premium_job():
    """Submit job with premium billing"""
    data = request.get_json()
    
    agent_name = data.get('agent_name')
    description = data.get('description')
    style = data.get('style', 'figurine')
    size_mm = data.get('size_mm', 50.0)
    
    if not all([agent_name, description]):
        return jsonify({"error": "agent_name and description required"}), 400
    
    success, message, job_id = premium_service.submit_job(
        agent_name, description, style, size_mm
    )
    
    if not success:
        return jsonify({"success": False, "error": message}), 400
    
    return jsonify({
        "success": True,
        "job_id": job_id,
        "message": message,
        "status_url": f"/api/premium/jobs/{job_id}"
    }), 201

@app.route('/api/business/stats')
def business_stats():
    """Business metrics dashboard"""
    return jsonify(premium_service.get_business_stats())

@app.route('/premium')
def premium_dashboard():
    """Premium business dashboard"""
    stats = premium_service.get_business_stats()
    
    dashboard_html = """
<!DOCTYPE html>
<html>
<head>
    <title>🚀 Agent3D Business Dashboard</title>
    <meta charset="utf-8">
    <style>
        body { font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #0a0a0a; color: #ffffff; }
        .header { text-align: center; margin-bottom: 30px; }
        .partnership { background: linear-gradient(45deg, #1a1a1a, #2a2a2a); padding: 20px; border-radius: 8px; margin-bottom: 30px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat { background: #1a1a1a; padding: 20px; border-radius: 8px; border: 1px solid #333; }
        .stat h3 { margin: 0 0 10px 0; color: #00ff88; }
        .stat .value { font-size: 2em; font-weight: bold; }
        .revenue { color: #ffaa00; }
        .agents { color: #00aaff; }
        .growth { color: #ff4488; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Agent3D Business Dashboard</h1>
        <p>The first AI agent-native 3D printing platform</p>
    </div>
    
    <div class="partnership">
        <h2>🤝 R2 & Pedro Partnership</h2>
        <p><strong>Technical Partner:</strong> R2 (Development, Operations)</p>
        <p><strong>Business Partner:</strong> Pedro (Investment, Strategy)</p>
        <p><strong>Mission:</strong> Democratize 3D printing for the AI agent ecosystem</p>
    </div>
    
    <div class="stats">
        <div class="stat revenue">
            <h3>💰 Revenue</h3>
            <div class="value">${{ "%.2f"|format(stats.estimated_revenue_usd) }}</div>
            <div>{{ stats.total_apc_earned }} APC earned</div>
        </div>
        <div class="stat agents">
            <h3>🤖 Total Agents</h3>
            <div class="value">{{ stats.agents_by_tier.values() | sum }}</div>
            <div>{{ stats.agents_by_tier.get('free', 0) }} Free, {{ stats.agents_by_tier.get('pro', 0) }} Pro, {{ stats.agents_by_tier.get('enterprise', 0) }} Enterprise</div>
        </div>
        <div class="stat growth">
            <h3>📈 Jobs Completed</h3>
            <div class="value">{{ stats.jobs_by_status.get('completed', 0) }}</div>
            <div>{{ stats.jobs_by_status.get('pending', 0) }} pending, {{ stats.jobs_by_status.get('failed', 0) }} failed</div>
        </div>
        <div class="stat">
            <h3>⚙️ Operations</h3>
            <div class="value">{{ stats.active_workers }}/3</div>
            <div>{{ stats.queue_size }} jobs in queue</div>
        </div>
    </div>
    
    <div style="background: #1a1a1a; padding: 20px; border-radius: 8px;">
        <h2>🎯 Next Steps</h2>
        <ul>
            <li><strong>Legal:</strong> Register Agent3D LLC</li>
            <li><strong>Payments:</strong> Integrate Stripe for APC purchases</li>
            <li><strong>Marketing:</strong> Launch on Moltbook m/agentskills</li>
            <li><strong>Partnerships:</strong> Connect with agent framework developers</li>
        </ul>
    </div>
</body>
</html>
    """
    
    return render_template_string(dashboard_html, stats=stats)

def main():
    """Start the premium service"""
    print("🚀 Starting Agent3D Premium Service")
    print("💼 Business Dashboard: http://localhost:5000/premium")
    print("🔌 Premium API: http://localhost:5000/api/premium/")
    print("-" * 50)
    
    # Start the premium worker
    premium_service.start_worker()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5001, debug=False)

if __name__ == "__main__":
    main()