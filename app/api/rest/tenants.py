from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.tenant import TenantCreate, TenantResponse
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantResponse, status_code=201)
def create_tenant(tenant_data: TenantCreate, db: Session = Depends(get_db)):
    """Create a new tenant"""
    try:
        tenant = TenantService.create_tenant(db, tenant_data)
        return tenant
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=List[TenantResponse])
def list_tenants(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all tenants"""
    tenants = TenantService.list_tenants(db, skip=skip, limit=limit)
    return tenants


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    """Get tenant by ID"""
    tenant = TenantService.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
