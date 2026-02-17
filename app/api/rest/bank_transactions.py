from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from typing import List, Optional

from app.core.database import get_db
from app.core.config import settings
from app.schemas.bank_transaction import BankTransactionImport, BankTransactionResponse
from app.services.tenant_service import TenantService
from app.services.bank_transaction_service import BankTransactionService

router = APIRouter(prefix="/tenants/{tenant_id}/bank-transactions", tags=["bank-transactions"])


def verify_tenant(tenant_id: int, db: Session = Depends(get_db)):
    """Dependency to verify tenant exists"""
    if not TenantService.verify_tenant_exists(db, tenant_id):
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_id


@router.post("/import", response_model=List[BankTransactionResponse], status_code=201, dependencies=[Depends(verify_tenant)])
def import_transactions(
    tenant_id: int,
    import_data: BankTransactionImport,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    """Bulk import bank transactions with idempotency support"""
    key = idempotency_key or import_data.idempotency_key

    try:
        transactions, _ = BankTransactionService.import_transactions(
            db, tenant_id, import_data.transactions, key
        )
        return transactions
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        is_dev = "test" in settings.database_url or "sqlite" in settings.database_url.lower()
        detail = f"Database integrity error: {error_msg}" if is_dev else "A transaction with this data already exists"
        raise HTTPException(status_code=409, detail=detail)
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = str(e) if hasattr(e, '__str__') else "Database error"
        is_dev = "test" in settings.database_url or "sqlite" in settings.database_url.lower()
        detail = f"Database error: {error_msg}" if is_dev else "Database error occurred while importing transactions"
        raise HTTPException(status_code=500, detail=detail)
    except Exception as e:
        is_dev = "test" in settings.database_url or "sqlite" in settings.database_url.lower()
        detail = f"Error: {str(e)}" if is_dev else "An unexpected error occurred while importing transactions"
        raise HTTPException(status_code=500, detail=detail)


@router.get("", response_model=List[BankTransactionResponse], dependencies=[Depends(verify_tenant)])
def list_transactions(
    tenant_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List bank transactions for a tenant"""
    transactions = BankTransactionService.list_transactions(db, tenant_id, skip=skip, limit=limit)
    return transactions
