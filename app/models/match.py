from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, DateTime, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class MatchStatus(str, enum.Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Numeric(5, 2), nullable=False)  # 0.00 to 100.00
    status = Column(Enum(MatchStatus), default=MatchStatus.PROPOSED, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="matches")
    invoice = relationship("Invoice", back_populates="matches")
    bank_transaction = relationship("BankTransaction", back_populates="matches")

    # Ensure one confirmed match per invoice/transaction
    __table_args__ = (
        Index("ix_tenant_invoice_transaction", "tenant_id", "invoice_id", "bank_transaction_id", unique=True),
    )
