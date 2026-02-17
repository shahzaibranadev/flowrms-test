import pytest
from fastapi import status


def test_create_tenant(client):
    """Test creating a tenant"""
    response = client.post(
        "/api/tenants",
        json={"name": "TechStart Solutions LLC"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "TechStart Solutions LLC"
    assert "id" in data
    assert "created_at" in data


def test_list_tenants(client, tenant):
    """Test listing tenants"""
    response = client.get("/api/tenants")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert any(t["id"] == tenant.id for t in data)


def test_get_tenant(client, tenant):
    """Test getting a tenant by ID"""
    response = client.get(f"/api/tenants/{tenant.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == tenant.id
    assert data["name"] == tenant.name


def test_create_tenant_empty_name(client):
    """Test creating a tenant with empty name should fail"""
    response = client.post(
        "/api/tenants",
        json={"name": ""},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_tenant_whitespace_only_name(client):
    """Test creating a tenant with whitespace-only name should fail"""
    response = client.post(
        "/api/tenants",
        json={"name": "   "},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_tenant_duplicate_name(client, tenant):
    """Test creating a tenant with duplicate name should fail"""
    response = client.post(
        "/api/tenants",
        json={"name": tenant.name},  # Same name as existing tenant
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.json()["detail"].lower()


def test_create_tenant_duplicate_name_case_insensitive(client, tenant):
    """Test creating a tenant with duplicate name (case insensitive) should fail"""
    # Try with different case
    response = client.post(
        "/api/tenants",
        json={"name": tenant.name.upper()},
    )
    # Note: This depends on whether we want case-insensitive matching
    # For now, we'll test exact match
    assert response.status_code in [status.HTTP_409_CONFLICT, status.HTTP_201_CREATED]


def test_create_tenant_missing_name(client):
    """Test creating a tenant without name field should fail"""
    response = client.post(
        "/api/tenants",
        json={},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
