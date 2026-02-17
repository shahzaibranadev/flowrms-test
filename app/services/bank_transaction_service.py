from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from decimal import Decimal
import hashlib
import json

from app.models.bank_transaction import BankTransaction
from app.schemas.bank_transaction import BankTransactionCreate
from app.services.idempotency_service import IdempotencyService


class BankTransactionService:
    @staticmethod
    def import_transactions(
        db: Session,
        tenant_id: int,
        transactions: List[BankTransactionCreate],
        idempotency_key: Optional[str] = None,
    ) -> Tuple[List[BankTransaction], bool]:
        """Import bank transactions with idempotency support. Returns (transactions, is_duplicate)"""
        transactions_dict = [tx.model_dump(mode='json') for tx in transactions]
        payload_hash = IdempotencyService.hash_payload(transactions_dict)

        if idempotency_key:
            stored_hash = IdempotencyService.get_payload_hash(db, tenant_id, idempotency_key)
            if stored_hash and stored_hash != payload_hash:
                raise ValueError("Idempotency key reused with different payload")
            
            existing_result = IdempotencyService.get_result(db, tenant_id, idempotency_key)
            if existing_result and isinstance(existing_result, dict):
                transaction_ids = existing_result.get("transaction_ids", [])
                if transaction_ids:
                    try:
                        existing_transactions = db.query(BankTransaction).filter(
                            and_(
                                BankTransaction.id.in_(transaction_ids),
                                BankTransaction.tenant_id == tenant_id
                            )
                        ).all()
                        if len(existing_transactions) == len(transaction_ids):
                            return existing_transactions, True
                    except Exception:
                        pass

        created_transactions = []
        new_transactions_to_add = []
        
        for tx_data in transactions:
            if tx_data.external_id:
                existing = db.query(BankTransaction).filter(
                    and_(
                        BankTransaction.tenant_id == tenant_id,
                        BankTransaction.external_id == tx_data.external_id
                    )
                ).first()
                if existing:
                    created_transactions.append(existing)
                    continue

            transaction = BankTransaction(
                tenant_id=tenant_id,
                external_id=tx_data.external_id,
                posted_at=tx_data.posted_at,
                amount=tx_data.amount,
                currency=tx_data.currency,
                description=tx_data.description,
            )
            new_transactions_to_add.append(transaction)
            created_transactions.append(transaction)
        
        if idempotency_key and not new_transactions_to_add and created_transactions:
            stored_hash = IdempotencyService.get_payload_hash(db, tenant_id, idempotency_key)
            if stored_hash and stored_hash != payload_hash:
                raise ValueError("Idempotency key reused with different payload")
            
            transaction_ids = [tx.id for tx in created_transactions]
            result_data = {"transaction_ids": transaction_ids}
            try:
                IdempotencyService.store_result(db, tenant_id, idempotency_key, payload_hash, result_data)
                db.commit()
            except Exception:
                db.rollback()
            return created_transactions, True
        
        for tx in new_transactions_to_add:
            db.add(tx)

        if new_transactions_to_add:
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                raise ValueError(f"Failed to import transactions: {str(e)}")

        for tx in created_transactions:
            if hasattr(tx, 'id') and tx.id is None:
                try:
                    db.refresh(tx)
                except Exception:
                    pass

        if idempotency_key and new_transactions_to_add:
            transaction_ids = [tx.id for tx in created_transactions]
            result_data = {"transaction_ids": transaction_ids}
            try:
                IdempotencyService.store_result(db, tenant_id, idempotency_key, payload_hash, result_data)
                db.commit()
            except Exception:
                db.rollback()
        elif idempotency_key and not new_transactions_to_add:
            transaction_ids = [tx.id for tx in created_transactions]
            result_data = {"transaction_ids": transaction_ids}
            existing_hash = IdempotencyService.get_payload_hash(db, tenant_id, idempotency_key)
            if not existing_hash:
                try:
                    IdempotencyService.store_result(db, tenant_id, idempotency_key, payload_hash, result_data)
                    db.commit()
                except Exception:
                    db.rollback()

        return created_transactions, False

    @staticmethod
    def get_transaction(db: Session, tenant_id: int, transaction_id: int) -> BankTransaction | None:
        """Get transaction by ID, ensuring tenant isolation"""
        return db.query(BankTransaction).filter(
            and_(
                BankTransaction.id == transaction_id,
                BankTransaction.tenant_id == tenant_id
            )
        ).first()

    @staticmethod
    def list_transactions(
        db: Session,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[BankTransaction]:
        """List transactions for a tenant"""
        return db.query(BankTransaction).filter(
            BankTransaction.tenant_id == tenant_id
        ).order_by(BankTransaction.posted_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_unmatched_transactions(db: Session, tenant_id: int) -> List[BankTransaction]:
        """Get transactions that don't have confirmed matches"""
        from app.models.match import Match, MatchStatus

        # Get all transaction IDs with confirmed matches
        matched_ids = db.query(Match.bank_transaction_id).filter(
            and_(
                Match.tenant_id == tenant_id,
                Match.status == MatchStatus.CONFIRMED
            )
        ).subquery()

        return db.query(BankTransaction).filter(
            and_(
                BankTransaction.tenant_id == tenant_id,
                ~BankTransaction.id.in_(db.query(matched_ids))
            )
        ).all()
