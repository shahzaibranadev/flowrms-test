import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.database import Base, get_db
from app.main import app
from app.models.tenant import Tenant
from app.models.vendor import Vendor
from app.models.invoice import Invoice, InvoiceStatus
from app.models.bank_transaction import BankTransaction
from app.models.match import Match, MatchStatus


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    # Drop all tables first to ensure clean state
    Base.metadata.drop_all(bind=engine)
    # Create all tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up: drop all tables after test
        try:
            Base.metadata.drop_all(bind=engine)
        except Exception:
            # Ignore errors during cleanup (e.g., table doesn't exist)
            pass


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database override"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def tenant(db):
    """Create a sample tenant with unique name"""
    # Use UUID to ensure unique tenant names across tests
    unique_id = str(uuid.uuid4())[:8]
    tenant = Tenant(name=f"Acme Corporation {unique_id}")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def vendor(db, tenant):
    """Create a sample vendor"""
    vendor = Vendor(tenant_id=tenant.id, name="Global Supplies Inc")
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@pytest.fixture
def invoice(db, tenant, vendor):
    """Create a sample invoice"""
    invoice = Invoice(
        tenant_id=tenant.id,
        vendor_id=vendor.id,
        invoice_number="INV-2024-001",
        amount=Decimal("100.00"),
        currency="USD",
        invoice_date=datetime.now(),
        description="Office supplies and equipment",
        status=InvoiceStatus.OPEN,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@pytest.fixture
def bank_transaction(db, tenant):
    """Create a sample bank transaction"""
    transaction = BankTransaction(
        tenant_id=tenant.id,
        external_id="CHK-2024-001",
        posted_at=datetime.now(),
        amount=Decimal("100.00"),
        currency="USD",
        description="ACH Payment - Office supplies invoice",
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction
