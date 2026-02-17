from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class VendorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Vendor name (required, unique per tenant)")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not empty or just whitespace"""
        if not v or not v.strip():
            raise ValueError("Vendor name cannot be empty")
        return v.strip()


class VendorResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True
