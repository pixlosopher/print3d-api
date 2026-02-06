"""
Real job service with Gemini + Meshy pipeline.

Processes jobs in background threads with database persistence.
"""

from __future__ import annotations

import os
import sys
import threading
import queue
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import base64

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config
from web.database import (
    get_db_session, get_db,
    create_job, get_job, update_job, list_jobs,
    JobStatusEnum
)


class RealJobService:
    """
    Job service with real Gemini + Meshy pipeline.
    Uses SQLite/PostgreSQL for persistence.
    """

    def __init__(self):
        self.config = get_config()
        self.job_queue: queue.Queue = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Lazy-load pipeline components
        self._image_gen = None
        self._mesh_gen = None

        # Load pending jobs from database on startup
        self._load_pending_jobs()

    def _load_pending_jobs(self):
        """Load any pending jobs from database (in case of restart)."""
        try:
            with get_db_session() as db:
                pending_jobs = db.query(get_job.__self__.__class__).filter(
                    get_job.__self__.__class__.status.in_([
                        JobStatusEnum.PENDING.value,
                        JobStatusEnum.GENERATING_IMAGE.value,
                        JobStatusEnum.CONVERTING_3D.value
                    ])
                ).all() if False else []  # Simplified for now
            # Re-queue any interrupted jobs
            # for job in pending_jobs:
            #     self.job_queue.put(job.id)
            #     print(f"[STARTUP] Re-queued interrupted job: {job.id}")
        except Exception as e:
            print(f"[STARTUP] Could not load pending jobs: {e}")

    @property
    def image_gen(self):
        """Lazy load image generator."""
        if self._image_gen is None:
            from image_gen import ImageGenerator
            self._image_gen = ImageGenerator(self.config)
        return self._image_gen

    @property
    def mesh_gen(self):
        """Lazy load mesh generator."""
        if self._mesh_gen is None:
            from mesh_gen import MeshGenerator
            self._mesh_gen = MeshGenerator(self.config)
        return self._mesh_gen

    def submit_job(self, agent_name: str, description: str, style: str, size_mm: float) -> str:
        """Submit a new job for full processing (image + 3D)."""
        # Generate unique job ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        import uuid
        job_id = f"job_{timestamp}_{uuid.uuid4().hex[:6]}"

        # Create job in database
        with get_db_session() as db:
            create_job(
                db=db,
                job_id=job_id,
                description=description,
                style=style,
                size_mm=size_mm,
                agent_name=agent_name,
            )

        # Add to processing queue
        self.job_queue.put(job_id)
        print(f"[{job_id}] Submitted: {description}")

        return job_id

    def submit_concept_job(self, agent_name: str, description: str, style: str) -> str:
        """
        Submit a job for 2D concept generation only.

        This is the new cost-efficient flow:
        - Only generates the 2D image
        - 3D generation happens after payment via generate_mesh_for_job()
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        import uuid
        job_id = f"concept_{timestamp}_{uuid.uuid4().hex[:6]}"

        # Create job in database with concept_only flag
        with get_db_session() as db:
            create_job(
                db=db,
                job_id=job_id,
                description=description,
                style=style,
                size_mm=0,  # Size determined at checkout
                agent_name=agent_name,
                concept_only=True,  # New flag
            )

        # Add to processing queue (will only generate 2D)
        self.job_queue.put(job_id)
        print(f"[{job_id}] Concept job submitted: {description}")

        return job_id

    def generate_mesh_for_job(
        self,
        job_id: str,
        mesh_style: str = "detailed",
        material_key: str = "plastic_white",
    ) -> bool:
        """
        Generate 3D mesh for an existing concept job.

        Called after payment is confirmed.
        """
        try:
            with get_db_session() as db:
                job = get_job(db, job_id)
                if not job:
                    print(f"[{job_id}] Job not found")
                    return False

                if not job.image_path:
                    print(f"[{job_id}] No concept image found")
                    return False

                # Save image_path before session closes (to avoid detached instance error)
                job_image_path = job.image_path

                # Update status
                update_job(db, job_id, status=JobStatusEnum.CONVERTING_3D.value, progress=50)

            print(f"[{job_id}] Generating 3D mesh (style: {mesh_style}, material: {material_key})...")

            # Build image path (use saved variable, not detached job object)
            image_path = self.output_dir / job_image_path.replace("/output/", "")

            # Convert image to data URI for Meshy
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            image_url_for_meshy = f"data:image/png;base64,{image_b64}"

            # Get mesh options based on style and material
            from mesh_options import MeshGenerationOptions
            mesh_options = MeshGenerationOptions.from_user_selection(mesh_style, material_key)

            # Progress callback
            def on_mesh_progress(progress: int):
                with get_db_session() as db:
                    update_job(db, job_id, progress=50 + int(progress * 0.5))

            # Generate mesh with custom options
            mesh_result = self.mesh_gen.from_image(
                image_url=image_url_for_meshy,
                output_dir=self.output_dir,
                format="glb",
                on_progress=on_mesh_progress,
                # Pass mesh options to Meshy (requires mesh_gen update)
                # model_type=mesh_options.model_type,
                # target_polycount=mesh_options.target_polycount,
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mesh_filename = f"{job_id}_{timestamp}.glb"

            # Rename the downloaded file
            if mesh_result.local_path:
                new_mesh_path = self.output_dir / mesh_filename
                mesh_result.local_path.rename(new_mesh_path)

            # Update database with mesh path and all format URLs
            import json
            mesh_url = mesh_result.glb_url or mesh_result.obj_url
            mesh_urls_json = json.dumps(mesh_result.model_urls) if mesh_result.model_urls else None

            with get_db_session() as db:
                update_job(
                    db, job_id,
                    mesh_path=f"/output/{mesh_filename}",
                    mesh_url=mesh_url,
                    mesh_urls_json=mesh_urls_json,  # Save all format URLs
                    progress=100,
                    status=JobStatusEnum.COMPLETED.value
                )

            print(f"[{job_id}] Mesh generated: /output/{mesh_filename}")
            print(f"[{job_id}] Available formats: {list(mesh_result.model_urls.keys())}")
            return True

        except Exception as e:
            with get_db_session() as db:
                update_job(
                    db, job_id,
                    status=JobStatusEnum.FAILED.value,
                    error_message=str(e)
                )
            print(f"[{job_id}] Mesh generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Get job status from database."""
        with get_db_session() as db:
            job = get_job(db, job_id)
            if not job:
                return None
            return job.to_dict()

    def list_jobs(self, agent_name: Optional[str] = None, limit: int = 20) -> list:
        """List recent jobs from database."""
        with get_db_session() as db:
            jobs = list_jobs(db, limit=limit)
            return [j.to_dict() for j in jobs]

    def process_job(self, job_id: str) -> bool:
        """Process a single job through the pipeline."""
        try:
            # Get job details first to check if concept_only
            with get_db_session() as db:
                job = get_job(db, job_id)
                if not job:
                    return False
                description = job.description
                style = job.style
                concept_only = getattr(job, 'concept_only', False) or job_id.startswith('concept_')

            # Step 1: Generate Image with Gemini
            with get_db_session() as db:
                update_job(db, job_id, status=JobStatusEnum.GENERATING_IMAGE.value, progress=20)

            print(f"[{job_id}] Generating image... (concept_only={concept_only})")

            # Map style string to ImageStyle enum
            from image_gen import ImageStyle
            style_map = {
                "figurine": ImageStyle.FIGURINE,
                "sculpture": ImageStyle.SCULPTURE,
                "character": ImageStyle.CHARACTER,
                "object": ImageStyle.OBJECT,
                "miniature": ImageStyle.MINIATURE,
            }
            image_style = style_map.get(style, ImageStyle.FIGURINE)

            # Generate image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"{job_id}_{timestamp}.png"
            image_path = self.output_dir / image_filename

            self.image_gen.generate(
                prompt=description,
                style=image_style,
                save_to=image_path,
            )

            # Update database with image path
            with get_db_session() as db:
                update_job(
                    db, job_id,
                    image_path=f"/output/{image_filename}",
                    image_url=f"/output/{image_filename}",
                    progress=40 if not concept_only else 100,
                    status=JobStatusEnum.GENERATING_IMAGE.value if not concept_only else "concept_ready",
                )

            print(f"[{job_id}] Image generated: /output/{image_filename}")

            # If concept_only, stop here (3D generation happens after payment)
            if concept_only:
                print(f"[{job_id}] Concept ready! Waiting for payment before 3D generation.")
                return True

            # Step 2: Convert to 3D with Meshy
            with get_db_session() as db:
                update_job(db, job_id, status=JobStatusEnum.CONVERTING_3D.value, progress=50)

            print(f"[{job_id}] Converting to 3D...")

            # Convert image to data URI for Meshy
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            image_url_for_meshy = f"data:image/png;base64,{image_b64}"
            print(f"[{job_id}] Using data URI for Meshy ({len(image_b64)} bytes)")

            # Progress callback
            def on_mesh_progress(progress: int):
                with get_db_session() as db:
                    update_job(db, job_id, progress=50 + int(progress * 0.4))

            # Generate mesh
            mesh_result = self.mesh_gen.from_image(
                image_url=image_url_for_meshy,
                output_dir=self.output_dir,
                format="glb",  # GLB works well for web preview
                on_progress=on_mesh_progress,
            )

            mesh_filename = f"{job_id}_{timestamp}.glb"
            # Rename the downloaded file
            if mesh_result.local_path:
                new_mesh_path = self.output_dir / mesh_filename
                mesh_result.local_path.rename(new_mesh_path)

            # Update database with mesh path and all format URLs
            import json
            mesh_url = mesh_result.glb_url or mesh_result.obj_url
            mesh_urls_json = json.dumps(mesh_result.model_urls) if mesh_result.model_urls else None

            with get_db_session() as db:
                update_job(
                    db, job_id,
                    mesh_path=f"/output/{mesh_filename}",
                    mesh_url=mesh_url,
                    mesh_urls_json=mesh_urls_json,  # Save all format URLs
                    progress=100,
                    status=JobStatusEnum.COMPLETED.value
                )

            print(f"[{job_id}] Completed! Mesh: /output/{mesh_filename}")
            print(f"[{job_id}] Available formats: {list(mesh_result.model_urls.keys())}")
            return True

        except Exception as e:
            with get_db_session() as db:
                update_job(
                    db, job_id,
                    status=JobStatusEnum.FAILED.value,
                    error_message=str(e)
                )
            print(f"[{job_id}] Failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def worker_loop(self):
        """Background worker to process jobs."""
        print("[WORKER] Job worker started")

        while True:
            try:
                job_id = self.job_queue.get(timeout=5)
                print(f"[WORKER] Processing job: {job_id}")
                self.process_job(job_id)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[WORKER] Error: {e}")
                import traceback
                traceback.print_exc()

    def start_worker(self):
        """Start the background worker thread."""
        if self.worker_thread and self.worker_thread.is_alive():
            return

        self.worker_thread = threading.Thread(target=self.worker_loop, daemon=True)
        self.worker_thread.start()
        print("[WORKER] Job worker thread started")


# Singleton instance
_job_service: Optional[RealJobService] = None


def get_job_service() -> RealJobService:
    """Get the job service singleton."""
    global _job_service
    if _job_service is None:
        _job_service = RealJobService()
    return _job_service
