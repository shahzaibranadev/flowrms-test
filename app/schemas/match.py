from pydantic import BaseModel, field_serializer
from datetime import datetime
from typing import List
from decimal import Decimal
from app.models.match import MatchStatus


class MatchResponse(BaseModel):
    id: int
    tenant_id: int
    invoice_id: int
    bank_transaction_id: int
    score: Decimal
    status: MatchStatus
    created_at: datetime

    @field_serializer('score')
    def serialize_score(self, value: Decimal) -> str:
        """Serialize score to 2 decimal places"""
        return str(value.quantize(Decimal("0.01")))

    class Config:
        from_attributes = True


class MatchCandidate(BaseModel):
    invoice_id: int
    bank_transaction_id: int
    score: Decimal
    reason: str  # Brief explanation of why this match was proposed

    @field_serializer('score')
    def serialize_score(self, value: Decimal) -> str:
        """Serialize score to 2 decimal places"""
        return str(value.quantize(Decimal("0.01")))


class ReconciliationResponse(BaseModel):
    candidates: List[MatchCandidate]
    total_invoices: int
    total_transactions: int
    matches_found: int


class MatchConfirm(BaseModel):
    match_id: int
