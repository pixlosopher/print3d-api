"""
Database models and session management for print3d.

Uses SQLAlchemy with SQLite by default, supports PostgreSQL for production.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Enum as SQLEnum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import enum


# Get database URL from environment or use SQLite on persistent disk
# Note: /app/output is mounted as persistent storage on Render
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/output/print3d.db")

# SQLite specific: check_same_thread=False for multi-threaded access
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class JobStatusEnum(str, enum.Enum):
    """Job status enumeration."""
    PENDING = "pending"
    GENERATING_IMAGE = "generating_image"
    CONCEPT_READY = "concept_ready"  # New: 2D image ready, waiting for payment
    CONVERTING_3D = "converting_3d"
    COMPLETED = "completed"
    FAILED = "failed"


class OrderStatusEnum(str, enum.Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class JobModel(Base):
    """Database model for generation jobs."""
    __tablename__ = "jobs"

    id = Column(String(50), primary_key=True, index=True)
    description = Column(Text, nullable=False)
    style = Column(String(50), default="figurine")
    size_mm = Column(Float, default=50.0)
    status = Column(String(50), default=JobStatusEnum.PENDING.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Generated file paths
    image_path = Column(String(255), nullable=True)
    image_url = Column(String(500), nullable=True)
    mesh_path = Column(String(255), nullable=True)
    mesh_url = Column(String(500), nullable=True)

    # Progress and errors
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Agent info
    agent_name = Column(String(100), nullable=True)

    # New: concept-only flag for cost-efficient flow
    concept_only = Column(Boolean, default=False)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "description": self.description,
            "style": self.style,
            "size_mm": self.size_mm,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "image_path": self.image_path,
            "image_url": self.image_url,
            "mesh_path": self.mesh_path,
            "mesh_url": self.mesh_url,
            "progress": self.progress,
            "error_message": self.error_message,
            "agent_name": self.agent_name,
            "concept_only": self.concept_only,
        }


class OrderModel(Base):
    """Database model for orders."""
    __tablename__ = "orders"

    id = Column(String(50), primary_key=True, index=True)
    job_id = Column(String(50), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    status = Column(String(50), default=OrderStatusEnum.PENDING.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Product details
    size = Column(String(20), nullable=False)  # mini, small, medium, large, xl
    material = Column(String(50), nullable=False)
    color = Column(String(50), nullable=True)  # New: color selection
    mesh_style = Column(String(20), default="detailed")  # New: detailed or stylized
    price_usd = Column(Float, nullable=False)

    # Shipping address
    shipping_name = Column(String(255), nullable=True)
    shipping_address = Column(Text, nullable=True)
    shipping_city = Column(String(100), nullable=True)
    shipping_state = Column(String(100), nullable=True)
    shipping_zip = Column(String(20), nullable=True)
    shipping_country = Column(String(100), nullable=True)

    # Payment info
    payment_provider = Column(String(20), nullable=True)  # stripe, paypal
    payment_intent_id = Column(String(255), nullable=True)
    stripe_session_id = Column(String(255), nullable=True)

    # Fulfillment
    shapeways_order_id = Column(String(100), nullable=True)
    tracking_number = Column(String(100), nullable=True)
    tracking_url = Column(String(500), nullable=True)

    # External provider tracking (for semi-manual workflow)
    external_provider = Column(String(50), nullable=True)  # craftcloud, trideo, sculpteo, etc.
    external_order_id = Column(String(100), nullable=True)  # Order ID in external system
    production_cost_usd = Column(Float, nullable=True)  # Actual cost paid to provider
    shipping_cost_usd = Column(Float, nullable=True)  # Actual shipping cost
    admin_notes = Column(Text, nullable=True)  # Internal notes for admin

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "email": self.email,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "size": self.size,
            "material": self.material,
            "color": self.color,
            "mesh_style": self.mesh_style,
            "price_usd": self.price_usd,
            "shipping": {
                "name": self.shipping_name,
                "address": self.shipping_address,
                "city": self.shipping_city,
                "state": self.shipping_state,
                "zip": self.shipping_zip,
                "country": self.shipping_country,
            },
            "payment_provider": self.payment_provider,
            "shapeways_order_id": self.shapeways_order_id,
            "tracking_number": self.tracking_number,
            "tracking_url": self.tracking_url,
            # External provider fields
            "external_provider": self.external_provider,
            "external_order_id": self.external_order_id,
            "production_cost_usd": self.production_cost_usd,
            "shipping_cost_usd": self.shipping_cost_usd,
            "admin_notes": self.admin_notes,
        }


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    print("[DB] Database initialized")


def get_db() -> Session:
    """Get database session."""
    return SessionLocal()


@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Job CRUD operations
def create_job(
    db: Session,
    job_id: str,
    description: str,
    style: str,
    size_mm: float,
    agent_name: str = None,
    concept_only: bool = False,
) -> JobModel:
    """Create a new job in the database."""
    job = JobModel(
        id=job_id,
        description=description,
        style=style,
        size_mm=size_mm,
        agent_name=agent_name,
        status=JobStatusEnum.PENDING.value,
        concept_only=concept_only,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: str) -> Optional[JobModel]:
    """Get job by ID."""
    return db.query(JobModel).filter(JobModel.id == job_id).first()


def update_job(db: Session, job_id: str, **kwargs) -> Optional[JobModel]:
    """Update job fields."""
    job = get_job(db, job_id)
    if job:
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
    return job


def list_jobs(db: Session, limit: int = 20, offset: int = 0) -> list[JobModel]:
    """List recent jobs."""
    return db.query(JobModel).order_by(JobModel.created_at.desc()).offset(offset).limit(limit).all()


# Order CRUD operations
def create_order(
    db: Session,
    order_id: str,
    job_id: str,
    email: str,
    size: str,
    material: str,
    price_usd: float,
    shipping: dict = None,
    color: str = None,
    mesh_style: str = "detailed",
) -> OrderModel:
    """Create a new order in the database."""
    order = OrderModel(
        id=order_id,
        job_id=job_id,
        email=email,
        size=size,
        material=material,
        color=color,
        mesh_style=mesh_style,
        price_usd=price_usd,
        status=OrderStatusEnum.PENDING.value,
    )
    if shipping:
        order.shipping_name = shipping.get("name")
        order.shipping_address = shipping.get("address")
        order.shipping_city = shipping.get("city")
        order.shipping_state = shipping.get("state")
        order.shipping_zip = shipping.get("zip")
        order.shipping_country = shipping.get("country")
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_order(db: Session, order_id: str) -> Optional[OrderModel]:
    """Get order by ID."""
    return db.query(OrderModel).filter(OrderModel.id == order_id).first()


def get_order_by_stripe_session(db: Session, session_id: str) -> Optional[OrderModel]:
    """Get order by Stripe session ID."""
    return db.query(OrderModel).filter(OrderModel.stripe_session_id == session_id).first()


def update_order(db: Session, order_id: str, **kwargs) -> Optional[OrderModel]:
    """Update order fields."""
    order = get_order(db, order_id)
    if order:
        for key, value in kwargs.items():
            if hasattr(order, key):
                setattr(order, key, value)
        order.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
    return order


def list_orders_by_email(db: Session, email: str, limit: int = 20) -> list[OrderModel]:
    """List orders by email."""
    return db.query(OrderModel).filter(OrderModel.email == email).order_by(OrderModel.created_at.desc()).limit(limit).all()


def list_orders_for_admin(
    db: Session,
    status: str = None,
    limit: int = 50,
    offset: int = 0,
) -> list[OrderModel]:
    """List orders for admin dashboard with optional status filter."""
    query = db.query(OrderModel)
    if status:
        query = query.filter(OrderModel.status == status)
    return query.order_by(OrderModel.created_at.desc()).offset(offset).limit(limit).all()


def count_orders_by_status(db: Session) -> dict:
    """Count orders by status for admin dashboard."""
    from sqlalchemy import func
    results = db.query(
        OrderModel.status,
        func.count(OrderModel.id)
    ).group_by(OrderModel.status).all()
    return {status: count for status, count in results}


# Initialize on import
init_db()
