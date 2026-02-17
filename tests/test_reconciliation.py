import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import status

from app.models.invoice import Invoice, InvoiceStatus
from app.models.bank_transaction import BankTransaction
from app.models.match import Match, MatchStatus


def test_reconciliation_creates_candidates(client, tenant, invoice, bank_transaction, db):
    """Test that reconciliation creates match candidates"""
    # Ensure invoice and transaction match
    invoice.amount = Decimal("100.00")
    bank_transaction.amount = Decimal("100.00")
    invoice.invoice_date = datetime.now()
    bank_transaction.posted_at = datetime.now()
    db.commit()

    response = client.post(f"/api/tenants/{tenant.id}/reconcile")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "candidates" in data
    assert len(data["candidates"]) > 0
    assert data["matches_found"] > 0


def test_reconciliation_ranking(client, tenant, db):
    """Test that reconciliation produces expected ranking behavior"""
    now = datetime.now()
    # Create invoices with descriptions to ensure text similarity points
    invoice1 = Invoice(
        tenant_id=tenant.id,
        amount=Decimal("100.00"),
        currency="USD",
        invoice_date=now,
        description="Exact match test invoice",
        status=InvoiceStatus.OPEN,
    )
    invoice2 = Invoice(
        tenant_id=tenant.id,
        amount=Decimal("200.00"),
        currency="USD",
        invoice_date=now,
        description="Close match test invoice",
        status=InvoiceStatus.OPEN,
    )
    db.add_all([invoice1, invoice2])
    db.commit()

    # Create transactions - one perfect match, one with date difference
    # Perfect match should score higher
    transaction1 = BankTransaction(
        tenant_id=tenant.id,
        amount=Decimal("100.00"),  # Exact amount match
        currency="USD",
        posted_at=now,  # Same date
        description="Exact match test invoice",  # Same text
    )
    transaction2 = BankTransaction(
        tenant_id=tenant.id,
        amount=Decimal("200.00"),  # Exact amount match
        currency="USD",
        posted_at=now - timedelta(days=3),  # 3 days difference (at tolerance edge, lower date score)
        description="Close match test invoice",  # Same text
    )
    db.add_all([transaction1, transaction2])
    db.commit()

    response = client.post(f"/api/tenants/{tenant.id}/reconcile")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Find matches
    match1 = next(
        (c for c in data["candidates"] if c["invoice_id"] == invoice1.id), None
    )
    match2 = next(
        (c for c in data["candidates"] if c["invoice_id"] == invoice2.id), None
    )

    assert match1 is not None
    assert match2 is not None
    # Perfect match (same date) should have higher score than match with date difference
    assert Decimal(match1["score"]) > Decimal(match2["score"])


def test_confirm_match(client, tenant, invoice, bank_transaction, db):
    """Test confirming a match"""
    # Create a proposed match
    match = Match(
        tenant_id=tenant.id,
        invoice_id=invoice.id,
        bank_transaction_id=bank_transaction.id,
        score=Decimal("85.00"),
        status=MatchStatus.PROPOSED,
    )
    db.add(match)
    db.commit()

    response = client.post(
        f"/api/tenants/{tenant.id}/reconcile/matches/{match.id}/confirm"
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "confirmed"

    # Verify invoice status updated
    db.refresh(invoice)
    assert invoice.status == InvoiceStatus.MATCHED


def test_confirm_nonexistent_match(client, tenant):
    """Test confirming a non-existent match"""
    response = client.post(
        f"/api/tenants/{tenant.id}/reconcile/matches/99999/confirm"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_explain_reconciliation(client, tenant, invoice, bank_transaction):
    """Test AI explanation endpoint"""
    response = client.get(
        f"/api/tenants/{tenant.id}/reconcile/explain",
        params={
            "invoice_id": invoice.id,
            "transaction_id": bank_transaction.id,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "explanation" in data
    assert "score" in data
    assert len(data["explanation"]) > 0  # Should have some explanation


def test_explain_reconciliation_fallback(client, tenant, invoice, bank_transaction, monkeypatch):
    """Test that explanation falls back when AI is unavailable"""
    # Disable AI
    monkeypatch.setenv("AI_ENABLED", "false")

    response = client.get(
        f"/api/tenants/{tenant.id}/reconcile/explain",
        params={
            "invoice_id": invoice.id,
            "transaction_id": bank_transaction.id,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "explanation" in data
    # Should still return deterministic explanation
    assert len(data["explanation"]) > 0
