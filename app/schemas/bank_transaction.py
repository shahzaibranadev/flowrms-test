from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List
from decimal import Decimal


class BankTransactionCreate(BaseModel):
    external_id: Optional[str] = Field(None, max_length=255, description="External transaction ID (unique per tenant)")
    posted_at: datetime = Field(..., description="Transaction posted date/time")
    amount: Decimal = Field(..., gt=0, description="Transaction amount (must be positive)")
    currency: str = Field(default="USD", max_length=10, description="Currency code")
    description: Optional[str] = Field(None, max_length=1000, description="Transaction description")

    @field_validator('external_id')
    @classmethod
    def validate_external_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate external_id is not empty if provided"""
        if v is not None and (not v or not v.strip()):
            raise ValueError("External ID cannot be empty if provided")
        return v.strip() if v else None

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate description is not empty if provided"""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Description cannot be empty if provided")
        return v.strip() if v else None

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency is not empty"""
        if not v or not v.strip():
            raise ValueError("Currency cannot be empty")
        return v.strip().upper()


class BankTransactionImport(BaseModel):
    transactions: List[BankTransactionCreate]
    idempotency_key: Optional[str] = None


class BankTransactionResponse(BaseModel):
    id: int
    tenant_id: int
    external_id: Optional[str]
    posted_at: datetime
    amount: Decimal
    currency: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
