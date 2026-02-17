from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
from decimal import Decimal
from app.models.invoice import InvoiceStatus


class InvoiceCreate(BaseModel):
    vendor_id: Optional[int] = None
    invoice_number: Optional[str] = Field(None, max_length=255, description="Invoice number (unique per tenant)")
    amount: Decimal = Field(..., gt=0, description="Invoice amount (must be positive)")
    currency: str = Field(default="USD", max_length=10, description="Currency code")
    invoice_date: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=1000, description="Invoice description")

    @field_validator('invoice_number')
    @classmethod
    def validate_invoice_number(cls, v: Optional[str]) -> Optional[str]:
        """Validate invoice number is not empty if provided"""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Invoice number cannot be empty if provided")
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


class InvoiceFilter(BaseModel):
    status: Optional[InvoiceStatus] = None
    vendor_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None


class InvoiceResponse(BaseModel):
    id: int
    tenant_id: int
    vendor_id: Optional[int]
    invoice_number: Optional[str]
    amount: Decimal
    currency: str
    invoice_date: Optional[datetime]
    description: Optional[str]
    status: InvoiceStatus
    created_at: datetime

    class Config:
        from_attributes = True
