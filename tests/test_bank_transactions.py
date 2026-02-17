import pytest
from datetime import datetime
from decimal import Decimal
from fastapi import status


def test_import_bank_transactions(client, tenant):
    """Test importing bank transactions"""
    transactions_data = [
        {
            "external_id": "CHK-2024-001",
            "posted_at": datetime.now().isoformat(),
            "amount": "100.00",
            "currency": "USD",
            "description": "ACH Payment - Invoice #INV-2024-001",
        },
        {
            "external_id": "CHK-2024-002",
            "posted_at": datetime.now().isoformat(),
            "amount": "200.00",
            "currency": "USD",
            "description": "Wire Transfer - Monthly Subscription",
        },
    ]

    response = client.post(
        f"/api/tenants/{tenant.id}/bank-transactions/import",
        json={"transactions": transactions_data},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert len(data) == 2
    assert data[0]["external_id"] == "CHK-2024-001"
    assert data[1]["external_id"] == "CHK-2024-002"


def test_import_bank_transactions_idempotency(client, tenant):
    """Test idempotency of bank transaction imports"""
    transactions_data = [
        {
            "external_id": "TXN-IDEMPOTENT-001",
            "posted_at": datetime.now().isoformat(),
            "amount": "150.00",
            "currency": "USD",
            "description": "Payment for services rendered",
        }
    ]

    idempotency_key = "import-batch-2024-03-15-001"

    # First import
    response1 = client.post(
        f"/api/tenants/{tenant.id}/bank-transactions/import",
        json={"transactions": transactions_data, "idempotency_key": idempotency_key},
        headers={"Idempotency-Key": idempotency_key},
    )
    assert response1.status_code == status.HTTP_201_CREATED
    first_result = response1.json()
    first_ids = [tx["id"] for tx in first_result]

    # Second import with same key
    response2 = client.post(
        f"/api/tenants/{tenant.id}/bank-transactions/import",
        json={"transactions": transactions_data, "idempotency_key": idempotency_key},
        headers={"Idempotency-Key": idempotency_key},
    )
    assert response2.status_code == status.HTTP_201_CREATED
    second_result = response2.json()
    second_ids = [tx["id"] for tx in second_result]

    # Should return same transaction IDs
    assert first_ids == second_ids


def test_import_bank_transactions_idempotency_conflict(client, tenant):
    """Test idempotency key conflict with different payload"""
    idempotency_key = "import-batch-2024-03-15-conflict"

    # First import
    transactions1 = [
        {
            "external_id": "CHK-CONFLICT-A",
            "posted_at": datetime.now().isoformat(),
            "amount": "100.00",
            "currency": "USD",
            "description": "Initial payment batch",
        }
    ]
    response1 = client.post(
        f"/api/tenants/{tenant.id}/bank-transactions/import",
        json={"transactions": transactions1, "idempotency_key": idempotency_key},
    )
    assert response1.status_code == status.HTTP_201_CREATED

    # Second import with same key but different payload
    transactions2 = [
        {
            "external_id": "CHK-CONFLICT-B",
            "posted_at": datetime.now().isoformat(),
            "amount": "200.00",
            "currency": "USD",
            "description": "Different payment batch",
        }
    ]
    response2 = client.post(
        f"/api/tenants/{tenant.id}/bank-transactions/import",
        json={"transactions": transactions2, "idempotency_key": idempotency_key},
    )
    # Should return conflict
    assert response2.status_code == status.HTTP_409_CONFLICT


def test_list_bank_transactions(client, tenant, bank_transaction):
    """Test listing bank transactions"""
    response = client.get(f"/api/tenants/{tenant.id}/bank-transactions")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert any(tx["id"] == bank_transaction.id for tx in data)


def test_import_transaction_duplicate_external_id(client, tenant):
    """Test importing transaction with duplicate external_id should return existing"""
    transactions_data = [
        {
            "external_id": "CHK-DUPLICATE-001",
            "posted_at": datetime.now().isoformat(),
            "amount": "100.00",
            "currency": "USD",
        }
    ]

    # First import
    response1 = client.post(
        f"/api/tenants/{tenant.id}/bank-transactions/import",
        json={"transactions": transactions_data},
    )
    assert response1.status_code == status.HTTP_201_CREATED
    first_id = response1.json()[0]["id"]

    # Second import with same external_id
    response2 = client.post(
        f"/api/tenants/{tenant.id}/bank-transactions/import",
        json={"transactions": transactions_data},
    )
    assert response2.status_code == status.HTTP_201_CREATED
    second_id = response2.json()[0]["id"]

    # Should return same transaction (idempotent by external_id)
    assert first_id == second_id


def test_import_transaction_negative_amount(client, tenant):
    """Test importing transaction with negative amount should fail"""
    transactions_data = [
        {
            "external_id": "CHK-NEGATIVE",
            "posted_at": datetime.now().isoformat(),
            "amount": "-100.00",
            "currency": "USD",
        }
    ]

    response = client.post(
        f"/api/tenants/{tenant.id}/bank-transactions/import",
        json={"transactions": transactions_data},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_import_transaction_zero_amount(client, tenant):
    """Test importing transaction with zero amount should fail"""
    transactions_data = [
        {
            "external_id": "CHK-ZERO",
            "posted_at": datetime.now().isoformat(),
            "amount": "0.00",
            "currency": "USD",
        }
    ]

    response = client.post(
        f"/api/tenants/{tenant.id}/bank-transactions/import",
        json={"transactions": transactions_data},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_import_transaction_empty_currency(client, tenant):
    """Test importing transaction with empty currency should fail"""
    transactions_data = [
        {
            "external_id": "CHK-EMPTY-CURRENCY",
            "posted_at": datetime.now().isoformat(),
            "amount": "100.00",
            "currency": "",
        }
    ]

    response = client.post(
        f"/api/tenants/{tenant.id}/bank-transactions/import",
        json={"transactions": transactions_data},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_import_transaction_empty_external_id(client, tenant):
    """Test importing transaction with empty external_id should fail"""
    transactions_data = [
        {
            "external_id": "",
            "posted_at": datetime.now().isoformat(),
            "amount": "100.00",
            "currency": "USD",
        }
    ]

    response = client.post(
        f"/api/tenants/{tenant.id}/bank-transactions/import",
        json={"transactions": transactions_data},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
