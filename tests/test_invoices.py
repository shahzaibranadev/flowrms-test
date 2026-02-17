import pytest
from datetime import datetime
from decimal import Decimal
from fastapi import status

from app.models.invoice import InvoiceStatus


def test_create_invoice(client, tenant):
    """Test creating an invoice"""
    response = client.post(
        f"/api/tenants/{tenant.id}/invoices",
        json={
            "amount": "150.00",
            "currency": "USD",
            "invoice_number": "INV-2024-002",
            "description": "Monthly software subscription",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["amount"] == "150.00"
    assert data["currency"] == "USD"
    assert data["invoice_number"] == "INV-2024-002"
    assert data["status"] == "open"
    assert data["tenant_id"] == tenant.id


def test_list_invoices(client, tenant, invoice):
    """Test listing invoices"""
    response = client.get(f"/api/tenants/{tenant.id}/invoices")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert any(inv["id"] == invoice.id for inv in data)


def test_list_invoices_with_status_filter(client, tenant, invoice):
    """Test listing invoices with status filter"""
    response = client.get(
        f"/api/tenants/{tenant.id}/invoices",
        params={"status": "open"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(inv["status"] == "open" for inv in data)


def test_list_invoices_with_amount_filter(client, tenant, invoice, db):
    """Test listing invoices with amount filter"""
    # Create another invoice with different amount
    from app.models.invoice import Invoice, InvoiceStatus
    invoice2 = Invoice(
        tenant_id=tenant.id,
        amount=Decimal("200.00"),
        currency="USD",
        status=InvoiceStatus.OPEN,
    )
    db.add(invoice2)
    db.commit()

    # Filter by minimum amount
    response = client.get(
        f"/api/tenants/{tenant.id}/invoices",
        params={"amount_min": "150.00"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(Decimal(inv["amount"]) >= Decimal("150.00") for inv in data)


def test_delete_invoice(client, tenant, invoice):
    """Test deleting an invoice"""
    response = client.delete(f"/api/tenants/{tenant.id}/invoices/{invoice.id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify it's deleted
    response = client.get(f"/api/tenants/{tenant.id}/invoices")
    data = response.json()
    assert not any(inv["id"] == invoice.id for inv in data)


def test_delete_nonexistent_invoice(client, tenant):
    """Test deleting a non-existent invoice"""
    response = client.delete(f"/api/tenants/{tenant.id}/invoices/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_invoices_nonexistent_tenant(client):
    """Test listing invoices for non-existent tenant"""
    response = client.get("/api/tenants/99999/invoices")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_invoice_duplicate_invoice_number(client, tenant):
    """Test creating invoice with duplicate invoice number should fail"""
    # Create first invoice
    response1 = client.post(
        f"/api/tenants/{tenant.id}/invoices",
        json={
            "invoice_number": "INV-DUPLICATE-001",
            "amount": "100.00",
            "currency": "USD",
        },
    )
    assert response1.status_code == status.HTTP_201_CREATED

    # Try to create another with same invoice number
    response2 = client.post(
        f"/api/tenants/{tenant.id}/invoices",
        json={
            "invoice_number": "INV-DUPLICATE-001",
            "amount": "200.00",
            "currency": "USD",
        },
    )
    assert response2.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response2.json()["detail"].lower()


def test_create_invoice_empty_invoice_number(client, tenant):
    """Test creating invoice with empty invoice number should fail"""
    response = client.post(
        f"/api/tenants/{tenant.id}/invoices",
        json={
            "invoice_number": "",
            "amount": "100.00",
            "currency": "USD",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_invoice_whitespace_invoice_number(client, tenant):
    """Test creating invoice with whitespace-only invoice number should fail"""
    response = client.post(
        f"/api/tenants/{tenant.id}/invoices",
        json={
            "invoice_number": "   ",
            "amount": "100.00",
            "currency": "USD",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_invoice_negative_amount(client, tenant):
    """Test creating invoice with negative amount should fail"""
    response = client.post(
        f"/api/tenants/{tenant.id}/invoices",
        json={
            "amount": "-100.00",
            "currency": "USD",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_invoice_zero_amount(client, tenant):
    """Test creating invoice with zero amount should fail"""
    response = client.post(
        f"/api/tenants/{tenant.id}/invoices",
        json={
            "amount": "0.00",
            "currency": "USD",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_invoice_empty_currency(client, tenant):
    """Test creating invoice with empty currency should fail"""
    response = client.post(
        f"/api/tenants/{tenant.id}/invoices",
        json={
            "amount": "100.00",
            "currency": "",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_invoice_whitespace_currency(client, tenant):
    """Test creating invoice with whitespace-only currency should fail"""
    response = client.post(
        f"/api/tenants/{tenant.id}/invoices",
        json={
            "amount": "100.00",
            "currency": "   ",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_invoice_empty_description(client, tenant):
    """Test creating invoice with empty description should fail"""
    response = client.post(
        f"/api/tenants/{tenant.id}/invoices",
        json={
            "amount": "100.00",
            "currency": "USD",
            "description": "",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_invoice_same_data_different_tenant(client, tenant):
    """Test that same invoice data can exist for different tenants"""
    # Create tenant 2
    response_tenant = client.post(
        "/api/tenants",
        json={"name": "Another Company"},
    )
    tenant2_id = response_tenant.json()["id"]

    # Create invoice for tenant 1
    response1 = client.post(
        f"/api/tenants/{tenant.id}/invoices",
        json={
            "invoice_number": "INV-SHARED-001",
            "amount": "100.00",
            "currency": "USD",
        },
    )
    assert response1.status_code == status.HTTP_201_CREATED

    # Create same invoice for tenant 2 (should succeed)
    response2 = client.post(
        f"/api/tenants/{tenant2_id}/invoices",
        json={
            "invoice_number": "INV-SHARED-001",
            "amount": "100.00",
            "currency": "USD",
        },
    )
    assert response2.status_code == status.HTTP_201_CREATED
