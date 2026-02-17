from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('name', name='uq_tenant_name'),
    )

    # Relationships
    vendors = relationship("Vendor", back_populates="tenant", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="tenant", cascade="all, delete-orphan")
    bank_transactions = relationship("BankTransaction", back_populates="tenant", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="tenant", cascade="all, delete-orphan")
