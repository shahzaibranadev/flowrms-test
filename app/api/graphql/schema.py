import strawberry
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.tenant import TenantCreate, TenantResponse
from app.schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceFilter
from app.schemas.bank_transaction import BankTransactionCreate, BankTransactionResponse
from app.schemas.match import MatchCandidate, ReconciliationResponse, MatchResponse
from app.models.invoice import InvoiceStatus
from app.models.match import MatchStatus
from app.services.tenant_service import TenantService
from app.services.invoice_service import InvoiceService
from app.services.bank_transaction_service import BankTransactionService
from app.services.reconciliation_service import ReconciliationService
from app.services.ai_service import AIService


# GraphQL Types
@strawberry.type
class Tenant:
    id: int
    name: str
    created_at: datetime

    @classmethod
    def from_model(cls, tenant):
        return cls(
            id=tenant.id,
            name=tenant.name,
            created_at=tenant.created_at,
        )


@strawberry.type
class Invoice:
    id: int
    tenant_id: int
    vendor_id: Optional[int]
    invoice_number: Optional[str]
    amount: Decimal
    currency: str
    invoice_date: Optional[datetime]
    description: Optional[str]
    status: str
    created_at: datetime

    @classmethod
    def from_model(cls, invoice):
        return cls(
            id=invoice.id,
            tenant_id=invoice.tenant_id,
            vendor_id=invoice.vendor_id,
            invoice_number=invoice.invoice_number,
            amount=invoice.amount,
            currency=invoice.currency,
            invoice_date=invoice.invoice_date,
            description=invoice.description,
            status=invoice.status.value,
            created_at=invoice.created_at,
        )


@strawberry.type
class BankTransaction:
    id: int
    tenant_id: int
    external_id: Optional[str]
    posted_at: datetime
    amount: Decimal
    currency: str
    description: Optional[str]
    created_at: datetime

    @classmethod
    def from_model(cls, transaction):
        return cls(
            id=transaction.id,
            tenant_id=transaction.tenant_id,
            external_id=transaction.external_id,
            posted_at=transaction.posted_at,
            amount=transaction.amount,
            currency=transaction.currency,
            description=transaction.description,
            created_at=transaction.created_at,
        )


@strawberry.type
class MatchCandidate:
    invoice_id: int
    bank_transaction_id: int
    score: Decimal
    reason: str


@strawberry.type
class ReconciliationResult:
    candidates: List[MatchCandidate]
    total_invoices: int
    total_transactions: int
    matches_found: int


@strawberry.type
class Match:
    id: int
    tenant_id: int
    invoice_id: int
    bank_transaction_id: int
    score: Decimal
    status: str
    created_at: datetime

    @classmethod
    def from_model(cls, match):
        return cls(
            id=match.id,
            tenant_id=match.tenant_id,
            invoice_id=match.invoice_id,
            bank_transaction_id=match.bank_transaction_id,
            score=match.score,
            status=match.status.value,
            created_at=match.created_at,
        )


@strawberry.type
class Explanation:
    invoice_id: int
    transaction_id: int
    score: float
    explanation: str


# Input Types
@strawberry.input
class TenantInput:
    name: str


@strawberry.input
class InvoiceInput:
    vendor_id: Optional[int] = None
    invoice_number: Optional[str] = None
    amount: Decimal
    currency: str = "USD"
    invoice_date: Optional[datetime] = None
    description: Optional[str] = None


@strawberry.input
class BankTransactionInput:
    external_id: Optional[str] = None
    posted_at: datetime
    amount: Decimal
    currency: str = "USD"
    description: Optional[str] = None


@strawberry.input
class BankTransactionImportInput:
    transactions: List[BankTransactionInput]
    idempotency_key: Optional[str] = None


@strawberry.input
class InvoiceFilterInput:
    status: Optional[str] = None
    vendor_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None


# Queries
@strawberry.type
class Query:
    @strawberry.field
    def tenants(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        db = next(get_db())
        try:
            tenants = TenantService.list_tenants(db, skip=skip, limit=limit)
            return [Tenant.from_model(t) for t in tenants]
        finally:
            db.close()

    @strawberry.field
    def invoices(
        self,
        tenant_id: int,
        filters: Optional[InvoiceFilterInput] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Invoice]:
        db = next(get_db())
        try:
            # Verify tenant exists
            if not TenantService.verify_tenant_exists(db, tenant_id):
                raise ValueError("Tenant not found")

            # Convert filter input
            invoice_filter = None
            if filters:
                status = InvoiceStatus(filters.status) if filters.status else None
                invoice_filter = InvoiceFilter(
                    status=status,
                    vendor_id=filters.vendor_id,
                    date_from=filters.date_from,
                    date_to=filters.date_to,
                    amount_min=filters.amount_min,
                    amount_max=filters.amount_max,
                )

            invoices = InvoiceService.list_invoices(
                db, tenant_id, filters=invoice_filter, skip=skip, limit=limit
            )
            return [Invoice.from_model(i) for i in invoices]
        finally:
            db.close()

    @strawberry.field
    def bank_transactions(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[BankTransaction]:
        db = next(get_db())
        try:
            # Verify tenant exists
            if not TenantService.verify_tenant_exists(db, tenant_id):
                raise ValueError("Tenant not found")

            transactions = BankTransactionService.list_transactions(
                db, tenant_id, skip=skip, limit=limit
            )
            return [BankTransaction.from_model(t) for t in transactions]
        finally:
            db.close()

    @strawberry.field
    def match_candidates(
        self,
        tenant_id: int,
    ) -> List[MatchCandidate]:
        db = next(get_db())
        try:
            # Verify tenant exists
            if not TenantService.verify_tenant_exists(db, tenant_id):
                raise ValueError("Tenant not found")

            from app.models.match import Match, MatchStatus
            matches = db.query(Match).filter(
                Match.tenant_id == tenant_id,
                Match.status == MatchStatus.PROPOSED
            ).all()

            return [
                MatchCandidate(
                    invoice_id=m.invoice_id,
                    bank_transaction_id=m.bank_transaction_id,
                    score=m.score,
                    reason="Proposed match",
                )
                for m in matches
            ]
        finally:
            db.close()

    @strawberry.field
    def explain_reconciliation(
        self,
        tenant_id: int,
        invoice_id: int,
        transaction_id: int,
    ) -> Explanation:
        db = next(get_db())
        try:
            # Verify tenant exists
            if not TenantService.verify_tenant_exists(db, tenant_id):
                raise ValueError("Tenant not found")

            # Get invoice and transaction
            invoice = InvoiceService.get_invoice(db, tenant_id, invoice_id)
            if not invoice:
                raise ValueError("Invoice not found")

            transaction = BankTransactionService.get_transaction(db, tenant_id, transaction_id)
            if not transaction:
                raise ValueError("Bank transaction not found")

            # Calculate score
            score, _ = ReconciliationService._calculate_match_score(invoice, transaction)

            # Get explanation
            explanation = AIService.explain_match(invoice, transaction, score)

            return Explanation(
                invoice_id=invoice_id,
                transaction_id=transaction_id,
                score=float(score),
                explanation=explanation,
            )
        finally:
            db.close()


# Mutations
@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_tenant(self, input: TenantInput) -> Tenant:
        db = next(get_db())
        try:
            tenant = TenantService.create_tenant(db, TenantCreate(name=input.name))
            return Tenant.from_model(tenant)
        except ValueError as e:
            raise ValueError(str(e))
        finally:
            db.close()

    @strawberry.mutation
    def create_invoice(self, tenant_id: int, input: InvoiceInput) -> Invoice:
        db = next(get_db())
        try:
            # Verify tenant exists
            if not TenantService.verify_tenant_exists(db, tenant_id):
                raise ValueError("Tenant not found")

            invoice_data = InvoiceCreate(
                vendor_id=input.vendor_id,
                invoice_number=input.invoice_number,
                amount=input.amount,
                currency=input.currency,
                invoice_date=input.invoice_date,
                description=input.description,
            )
            invoice = InvoiceService.create_invoice(db, tenant_id, invoice_data)
            return Invoice.from_model(invoice)
        except ValueError as e:
            raise ValueError(str(e))
        finally:
            db.close()

    @strawberry.mutation
    def delete_invoice(self, tenant_id: int, invoice_id: int) -> bool:
        db = next(get_db())
        try:
            # Verify tenant exists
            if not TenantService.verify_tenant_exists(db, tenant_id):
                raise ValueError("Tenant not found")

            success = InvoiceService.delete_invoice(db, tenant_id, invoice_id)
            if not success:
                raise ValueError("Invoice not found")
            return True
        finally:
            db.close()

    @strawberry.mutation
    def import_bank_transactions(
        self,
        tenant_id: int,
        input: BankTransactionImportInput,
    ) -> List[BankTransaction]:
        db = next(get_db())
        try:
            # Verify tenant exists
            if not TenantService.verify_tenant_exists(db, tenant_id):
                raise ValueError("Tenant not found")

            # Convert input
            transactions = [
                BankTransactionCreate(
                    external_id=t.external_id,
                    posted_at=t.posted_at,
                    amount=t.amount,
                    currency=t.currency,
                    description=t.description,
                )
                for t in input.transactions
            ]

            transactions_result, _ = BankTransactionService.import_transactions(
                db, tenant_id, transactions, input.idempotency_key
            )
            return [BankTransaction.from_model(t) for t in transactions_result]
        except ValueError as e:
            raise ValueError(f"Import failed: {str(e)}")
        finally:
            db.close()

    @strawberry.mutation
    def reconcile(self, tenant_id: int) -> ReconciliationResult:
        db = next(get_db())
        try:
            # Verify tenant exists
            if not TenantService.verify_tenant_exists(db, tenant_id):
                raise ValueError("Tenant not found")

            result = ReconciliationService.reconcile(db, tenant_id)
            return ReconciliationResult(
                candidates=[
                    MatchCandidate(
                        invoice_id=c.invoice_id,
                        bank_transaction_id=c.bank_transaction_id,
                        score=c.score,
                        reason=c.reason,
                    )
                    for c in result.candidates
                ],
                total_invoices=result.total_invoices,
                total_transactions=result.total_transactions,
                matches_found=result.matches_found,
            )
        finally:
            db.close()

    @strawberry.mutation
    def confirm_match(self, tenant_id: int, match_id: int) -> Match:
        db = next(get_db())
        try:
            # Verify tenant exists
            if not TenantService.verify_tenant_exists(db, tenant_id):
                raise ValueError("Tenant not found")

            match = ReconciliationService.confirm_match(db, tenant_id, match_id)
            return Match.from_model(match)
        except ValueError as e:
            raise ValueError(str(e))
        finally:
            db.close()


# Create schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
