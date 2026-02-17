from sqlalchemy.orm import Session
from typing import List, Tuple, Dict
from decimal import Decimal
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from app.models.invoice import Invoice, InvoiceStatus
from app.models.bank_transaction import BankTransaction
from app.models.match import Match, MatchStatus
from app.schemas.match import MatchCandidate, ReconciliationResponse
from app.services.invoice_service import InvoiceService
from app.services.bank_transaction_service import BankTransactionService


class ReconciliationService:
    EXACT_AMOUNT_WEIGHT = Decimal("50.0")
    AMOUNT_TOLERANCE_WEIGHT = Decimal("30.0")
    DATE_PROXIMITY_WEIGHT = Decimal("15.0")
    TEXT_SIMILARITY_WEIGHT = Decimal("5.0")
    AMOUNT_TOLERANCE = Decimal("0.01")
    DATE_TOLERANCE_DAYS = 3
    MIN_SCORE_THRESHOLD = Decimal("20.0")

    @staticmethod
    def reconcile(db: Session, tenant_id: int) -> ReconciliationResponse:
        """Run reconciliation process to find match candidates"""
        invoices = InvoiceService.get_open_invoices(db, tenant_id)
        transactions = BankTransactionService.get_unmatched_transactions(db, tenant_id)

        best_matches: Dict[int, MatchCandidate] = {}

        for invoice in invoices:
            for transaction in transactions:
                if invoice.currency != transaction.currency:
                    continue

                score, reason = ReconciliationService._calculate_match_score(invoice, transaction)

                if score >= ReconciliationService.MIN_SCORE_THRESHOLD:
                    rounded_score = score.quantize(Decimal("0.01"))
                    candidate = MatchCandidate(
                        invoice_id=invoice.id,
                        bank_transaction_id=transaction.id,
                        score=rounded_score,
                        reason=reason,
                    )

                    if invoice.id not in best_matches or score > best_matches[invoice.id].score:
                        best_matches[invoice.id] = candidate

        candidates = list(best_matches.values())

        for candidate in candidates:
            existing = db.query(Match).filter(
                Match.tenant_id == tenant_id,
                Match.invoice_id == candidate.invoice_id,
                Match.bank_transaction_id == candidate.bank_transaction_id,
            ).first()

            if not existing:
                match = Match(
                    tenant_id=tenant_id,
                    invoice_id=candidate.invoice_id,
                    bank_transaction_id=candidate.bank_transaction_id,
                    score=candidate.score,
                    status=MatchStatus.PROPOSED,
                )
                db.add(match)

        db.commit()

        return ReconciliationResponse(
            candidates=candidates,
            total_invoices=len(invoices),
            total_transactions=len(transactions),
            matches_found=len(candidates),
        )

    @staticmethod
    def _calculate_match_score(invoice: Invoice, transaction: BankTransaction) -> Tuple[Decimal, str]:
        """Calculate match score between invoice and transaction. Returns (score, reason)"""
        score = Decimal("0.0")
        reasons = []

        amount_diff = abs(invoice.amount - transaction.amount)
        if amount_diff == 0:
            score += ReconciliationService.EXACT_AMOUNT_WEIGHT
            reasons.append("exact amount match")
        elif amount_diff <= ReconciliationService.AMOUNT_TOLERANCE:
            proportion = Decimal("1.0") - (amount_diff / ReconciliationService.AMOUNT_TOLERANCE)
            score += ReconciliationService.AMOUNT_TOLERANCE_WEIGHT * proportion
            reasons.append(f"amount within tolerance ({amount_diff})")
        else:
            reasons.append("amount mismatch")

        if invoice.invoice_date and transaction.posted_at:
            date_diff = abs((invoice.invoice_date - transaction.posted_at).days)
            if date_diff <= ReconciliationService.DATE_TOLERANCE_DAYS:
                proportion = Decimal("1.0") - (Decimal(str(date_diff)) / Decimal(str(ReconciliationService.DATE_TOLERANCE_DAYS)))
                score += ReconciliationService.DATE_PROXIMITY_WEIGHT * proportion
                reasons.append(f"date within {date_diff} days")
            else:
                reasons.append(f"date difference {date_diff} days")

        text_score = ReconciliationService._text_similarity_score(invoice, transaction)
        if text_score > 0:
            score += ReconciliationService.TEXT_SIMILARITY_WEIGHT * Decimal(str(text_score))
            reasons.append("text similarity match")

        score = min(score, Decimal("100.0"))
        score = score.quantize(Decimal("0.01"))

        reason = "; ".join(reasons) if reasons else "low confidence match"
        return score, reason

    @staticmethod
    def _text_similarity_score(invoice: Invoice, transaction: BankTransaction) -> float:
        """Calculate text similarity between invoice and transaction descriptions"""
        invoice_text = ""
        if invoice.invoice_number:
            invoice_text += invoice.invoice_number.lower()
        if invoice.description:
            invoice_text += " " + invoice.description.lower()
        if invoice.vendor and invoice.vendor.name:
            invoice_text += " " + invoice.vendor.name.lower()

        transaction_text = (transaction.description or "").lower()

        if not invoice_text or not transaction_text:
            return 0.0

        # Use SequenceMatcher for similarity
        similarity = SequenceMatcher(None, invoice_text, transaction_text).ratio()

        # Also check if one contains the other (stronger signal)
        if invoice_text in transaction_text or transaction_text in invoice_text:
            similarity = max(similarity, 0.8)

        return similarity

    @staticmethod
    def confirm_match(db: Session, tenant_id: int, match_id: int) -> Match:
        """Confirm a proposed match"""
        match = db.query(Match).filter(
            Match.id == match_id,
            Match.tenant_id == tenant_id,
            Match.status == MatchStatus.PROPOSED,
        ).first()

        if not match:
            raise ValueError("Match not found or already processed")

        # Update match status
        match.status = MatchStatus.CONFIRMED

        # Update invoice status
        invoice = db.query(Invoice).filter(Invoice.id == match.invoice_id).first()
        if invoice:
            invoice.status = InvoiceStatus.MATCHED

        db.commit()
        db.refresh(match)
        return match
