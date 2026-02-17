from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="vendors")
    invoices = relationship("Invoice", back_populates="vendor")

    # Unique constraint: vendor name must be unique per tenant
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_tenant_vendor_name'),
    )
