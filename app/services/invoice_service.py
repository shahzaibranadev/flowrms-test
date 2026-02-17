from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceFilter


class InvoiceService:
    @staticmethod
    def create_invoice(db: Session, tenant_id: int, invoice_data: InvoiceCreate) -> Invoice:
        """Create a new invoice for a tenant"""
        if invoice_data.invoice_number:
            existing_invoice = db.query(Invoice).filter(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.invoice_number == invoice_data.invoice_number
                )
            ).first()
            if existing_invoice:
                raise ValueError(f"Invoice with number '{invoice_data.invoice_number}' already exists for this tenant")

        invoice = Invoice(
            tenant_id=tenant_id,
            vendor_id=invoice_data.vendor_id,
            invoice_number=invoice_data.invoice_number,
            amount=invoice_data.amount,
            currency=invoice_data.currency,
            invoice_date=invoice_data.invoice_date,
            description=invoice_data.description,
            status=InvoiceStatus.OPEN,
        )
        db.add(invoice)
        try:
            db.commit()
            db.refresh(invoice)
            return invoice
        except IntegrityError as e:
            db.rollback()
            if 'uq_tenant_invoice_number' in str(e.orig):
                raise ValueError(f"Invoice with number '{invoice_data.invoice_number}' already exists for this tenant")
            raise

    @staticmethod
    def get_invoice(db: Session, tenant_id: int, invoice_id: int) -> Invoice | None:
        """Get invoice by ID, ensuring tenant isolation"""
        return db.query(Invoice).filter(
            and_(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
        ).first()

    @staticmethod
    def list_invoices(
        db: Session,
        tenant_id: int,
        filters: Optional[InvoiceFilter] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Invoice]:
        """List invoices for a tenant with optional filters"""
        query = db.query(Invoice).filter(Invoice.tenant_id == tenant_id)

        if filters:
            if filters.status:
                query = query.filter(Invoice.status == filters.status)
            if filters.vendor_id:
                query = query.filter(Invoice.vendor_id == filters.vendor_id)
            if filters.date_from:
                query = query.filter(Invoice.invoice_date >= filters.date_from)
            if filters.date_to:
                query = query.filter(Invoice.invoice_date <= filters.date_to)
            if filters.amount_min is not None:
                query = query.filter(Invoice.amount >= filters.amount_min)
            if filters.amount_max is not None:
                query = query.filter(Invoice.amount <= filters.amount_max)

        return query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def delete_invoice(db: Session, tenant_id: int, invoice_id: int) -> bool:
        """Delete an invoice, ensuring tenant isolation"""
        invoice = db.query(Invoice).filter(
            and_(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
        ).first()

        if invoice:
            db.delete(invoice)
            db.commit()
            return True
        return False

    @staticmethod
    def get_open_invoices(db: Session, tenant_id: int) -> List[Invoice]:
        """Get all open invoices for a tenant"""
        return db.query(Invoice).filter(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.status == InvoiceStatus.OPEN
            )
        ).all()
