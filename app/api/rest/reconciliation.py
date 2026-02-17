from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.schemas.match import ReconciliationResponse, MatchResponse
from app.services.tenant_service import TenantService
from app.services.reconciliation_service import ReconciliationService
from app.services.ai_service import AIService
from app.services.invoice_service import InvoiceService
from app.services.bank_transaction_service import BankTransactionService

router = APIRouter(prefix="/tenants/{tenant_id}/reconcile", tags=["reconciliation"])


def verify_tenant(tenant_id: int, db: Session = Depends(get_db)):
    """Dependency to verify tenant exists"""
    if not TenantService.verify_tenant_exists(db, tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_id


@router.post("", response_model=ReconciliationResponse, dependencies=[Depends(verify_tenant)])
def reconcile(tenant_id: int, db: Session = Depends(get_db)):
    """Run reconciliation process and return match candidates"""
    result = ReconciliationService.reconcile(db, tenant_id)
    return result


@router.get("/explain", dependencies=[Depends(verify_tenant)])
def explain_reconciliation(
    tenant_id: int,
    invoice_id: int = Query(..., description="Invoice ID"),
    transaction_id: int = Query(..., description="Bank Transaction ID"),
    db: Session = Depends(get_db),
):
    """Get AI explanation for a potential match between invoice and transaction"""
    invoice = InvoiceService.get_invoice(db, tenant_id, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    transaction = BankTransactionService.get_transaction(db, tenant_id, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Bank transaction not found")

    from app.services.reconciliation_service import ReconciliationService
    score, _ = ReconciliationService._calculate_match_score(invoice, transaction)
    explanation = AIService.explain_match(invoice, transaction, score)

    return {
        "invoice_id": invoice_id,
        "transaction_id": transaction_id,
        "score": float(score),
        "explanation": explanation,
    }


@router.post("/matches/{match_id}/confirm", response_model=MatchResponse, dependencies=[Depends(verify_tenant)])
def confirm_match(
    tenant_id: int,
    match_id: int,
    db: Session = Depends(get_db),
):
    """Confirm a proposed match"""
    try:
        match = ReconciliationService.confirm_match(db, tenant_id, match_id)
        return match
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
