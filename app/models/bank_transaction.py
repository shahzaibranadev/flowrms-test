from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id = Column(String, nullable=True, index=True)
    posted_at = Column(DateTime(timezone=True), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="USD", nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="bank_transactions")
    matches = relationship("Match", back_populates="bank_transaction")

    # Composite index for tenant + external_id for idempotency
    __table_args__ = (
        Index("ix_tenant_external_id", "tenant_id", "external_id", unique=True),
    )
