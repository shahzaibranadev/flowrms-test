from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantResponse


class TenantService:
    @staticmethod
    def create_tenant(db: Session, tenant_data: TenantCreate) -> Tenant:
        """Create a new tenant"""
        existing_tenant = db.query(Tenant).filter(Tenant.name == tenant_data.name).first()
        if existing_tenant:
            raise ValueError(f"Tenant with name '{tenant_data.name}' already exists")
        
        tenant = Tenant(name=tenant_data.name)
        db.add(tenant)
        try:
            db.commit()
            db.refresh(tenant)
            return tenant
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Tenant with name '{tenant_data.name}' already exists") from e

    @staticmethod
    def get_tenant(db: Session, tenant_id: int) -> Tenant | None:
        """Get tenant by ID"""
        return db.query(Tenant).filter(Tenant.id == tenant_id).first()

    @staticmethod
    def list_tenants(db: Session, skip: int = 0, limit: int = 100) -> List[Tenant]:
        """List all tenants"""
        return db.query(Tenant).offset(skip).limit(limit).all()

    @staticmethod
    def verify_tenant_exists(db: Session, tenant_id: int) -> bool:
        """Verify tenant exists"""
        return db.query(Tenant).filter(Tenant.id == tenant_id).first() is not None
