from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, DateTime, Enum, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class InvoiceStatus(str, enum.Enum):
    OPEN = "open"
    MATCHED = "matched"
    PAID = "paid"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)
    invoice_number = Column(String, nullable=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="USD", nullable=False)
    invoice_date = Column(DateTime(timezone=True), nullable=True)
    description = Column(String, nullable=True)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.OPEN, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="invoices")
    vendor = relationship("Vendor", back_populates="invoices")
    matches = relationship("Match", back_populates="invoice")

    # Unique constraint: invoice_number must be unique per tenant (when provided)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'invoice_number', name='uq_tenant_invoice_number'),
    )
