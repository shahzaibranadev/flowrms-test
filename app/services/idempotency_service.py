from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict, List, Any
import hashlib
import json

from app.core.database import Base


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    idempotency_key = Column(String, nullable=False, index=True)
    payload_hash = Column(String, nullable=False)
    result_data = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'idempotency_key', name='uq_tenant_idempotency_key'),
        {"sqlite_autoincrement": True},
    )


class IdempotencyService:
    @staticmethod
    def hash_payload(payload: Any) -> str:
        """Create a hash of the payload for consistency checking"""
        try:
            if hasattr(payload, 'model_dump'):
                payload = payload.model_dump(mode='json')
            elif hasattr(payload, 'dict'):
                payload = payload.dict()
            
            if isinstance(payload, list):
                converted_list = []
                for item in payload:
                    if hasattr(item, 'model_dump'):
                        converted_list.append(item.model_dump(mode='json'))
                    elif hasattr(item, 'dict'):
                        converted_list.append(item.dict())
                    else:
                        converted_list.append(item)
                payload = converted_list
            
            payload_str = json.dumps(payload, sort_keys=True, default=str)
            return hashlib.sha256(payload_str.encode()).hexdigest()
        except Exception:
            payload_str = str(payload)
            return hashlib.sha256(payload_str.encode()).hexdigest()

    @staticmethod
    def get_result(db: Session, tenant_id: int, idempotency_key: str) -> Optional[Dict]:
        """Get stored result for an idempotency key"""
        record = db.query(IdempotencyRecord).filter(
            IdempotencyRecord.tenant_id == tenant_id,
            IdempotencyRecord.idempotency_key == idempotency_key
        ).first()

        if record and record.result_data:
            result = json.loads(record.result_data)
            if isinstance(result, dict):
                return result
            elif isinstance(result, list):
                return {"transaction_ids": result}
            return {"transaction_ids": result if isinstance(result, list) else [result]}
        return None

    @staticmethod
    def get_payload_hash(db: Session, tenant_id: int, idempotency_key: str) -> Optional[str]:
        """Get stored payload hash for an idempotency key"""
        record = db.query(IdempotencyRecord).filter(
            IdempotencyRecord.tenant_id == tenant_id,
            IdempotencyRecord.idempotency_key == idempotency_key
        ).first()

        return record.payload_hash if record else None

    @staticmethod
    def store_result(
        db: Session,
        tenant_id: int,
        idempotency_key: str,
        payload_hash: str,
        result_data: Any,
    ):
        """Store idempotency result"""
        try:
            existing = db.query(IdempotencyRecord).filter(
                IdempotencyRecord.tenant_id == tenant_id,
                IdempotencyRecord.idempotency_key == idempotency_key
            ).first()

            if existing:
                existing.payload_hash = payload_hash
                existing.result_data = json.dumps(result_data, default=str)
            else:
                record = IdempotencyRecord(
                    tenant_id=tenant_id,
                    idempotency_key=idempotency_key,
                    payload_hash=payload_hash,
                    result_data=json.dumps(result_data, default=str),
                )
                db.add(record)
        except IntegrityError:
            existing = db.query(IdempotencyRecord).filter(
                IdempotencyRecord.tenant_id == tenant_id,
                IdempotencyRecord.idempotency_key == idempotency_key
            ).first()
            if existing:
                existing.payload_hash = payload_hash
                existing.result_data = json.dumps(result_data, default=str)
            else:
                raise
