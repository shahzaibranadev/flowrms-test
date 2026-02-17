from fastapi import APIRouter
from app.api.rest import tenants, invoices, bank_transactions, reconciliation

api_router = APIRouter()
api_router.include_router(tenants.router)
api_router.include_router(invoices.router)
api_router.include_router(bank_transactions.router)
api_router.include_router(reconciliation.router)
