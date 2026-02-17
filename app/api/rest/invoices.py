from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from app.core.database import get_db
from app.schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceFilter
from app.schemas.tenant import TenantResponse
from app.services.tenant_service import TenantService
from app.services.invoice_service import InvoiceService
from app.models.invoice import InvoiceStatus

router = APIRouter(prefix="/tenants/{tenant_id}/invoices", tags=["invoices"])


def verify_tenant(tenant_id: int, db: Session = Depends(get_db)):
    """Dependency to verify tenant exists"""
    if not TenantService.verify_tenant_exists(db, tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_id


@router.post("", response_model=InvoiceResponse, status_code=201, dependencies=[Depends(verify_tenant)])
def create_invoice(
    tenant_id: int,
    invoice_data: InvoiceCreate,
    db: Session = Depends(get_db),
):
    """Create a new invoice for a tenant"""
    try:
        invoice = InvoiceService.create_invoice(db, tenant_id, invoice_data)
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{invoice_id}", response_model=InvoiceResponse, dependencies=[Depends(verify_tenant)])
def get_invoice(
    tenant_id: int,
    invoice_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific invoice by ID"""
    invoice = InvoiceService.get_invoice(db, tenant_id, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("", response_model=List[InvoiceResponse], dependencies=[Depends(verify_tenant)])
def list_invoices(
    tenant_id: int,
    status: Optional[InvoiceStatus] = Query(None),
    vendor_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    amount_min: Optional[Decimal] = Query(None),
    amount_max: Optional[Decimal] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List invoices for a tenant with optional filters"""
    filters = InvoiceFilter(
        status=status,
        vendor_id=vendor_id,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
    )
    invoices = InvoiceService.list_invoices(db, tenant_id, filters=filters, skip=skip, limit=limit)
    return invoices


@router.delete("/{invoice_id}", status_code=204, dependencies=[Depends(verify_tenant)])
def delete_invoice(
    tenant_id: int,
    invoice_id: int,
    db: Session = Depends(get_db),
):
    """Delete an invoice"""
    success = InvoiceService.delete_invoice(db, tenant_id, invoice_id)
    if not success:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return None
