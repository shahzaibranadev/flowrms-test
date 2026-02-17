from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Tenant name (required, non-empty)")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not empty or just whitespace"""
        if not v or not v.strip():
            raise ValueError("Tenant name cannot be empty")
        return v.strip()


class TenantResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True
