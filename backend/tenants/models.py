"""Tenant (organization), TenantUser, TenantData, Department, and SessionProfile models."""
import uuid

from sqlalchemy import Column, String, Integer, Enum, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from models import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    config = Column(JSONB, nullable=False, default=dict)
    subscription_tier = Column(
        Enum("basic", "standard", "advanced", "flagship", name="subscription_tier"),
        nullable=False,
        default="basic",
    )
    status = Column(
        Enum("active", "suspended", "cancelled", name="tenant_status"),
        nullable=False,
        default="active",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TenantUser(Base):
    __tablename__ = "tenant_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(
        Enum("admin", "manager", "viewer", "department_head", name="tenant_user_role"),
        nullable=False,
        default="viewer",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TenantData(Base):
    __tablename__ = "tenant_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    data_type = Column(
        Enum("admission_score", "curriculum", "employment", "campus_life", name="tenant_data_type"),
        nullable=False,
    )
    title = Column(String(500), nullable=False)
    content = Column(JSONB, nullable=False, default=dict)
    source_url = Column(String(1000), default="")
    year = Column(Integer)
    province = Column(String(100))
    metadata = Column(JSONB, default=dict)  # noqa: F821 (shadowing stdlib)
    indexed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Department(Base):
    __tablename__ = "departments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    config = Column(JSONB, default=dict)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)


class SessionProfile(Base):
    __tablename__ = "session_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    profile_json = Column(JSONB, nullable=False, default=dict)
    confidence_json = Column(JSONB, nullable=False, default=dict)
    completeness = Column(String(10))  # L1 / L2 / L3
    created_at = Column(DateTime(timezone=True), server_default=func.now())
