from typing import Optional
from decimal import Decimal
from datetime import datetime

from app.core.config import settings
from app.models.invoice import Invoice
from app.models.bank_transaction import BankTransaction


class AIService:
    @staticmethod
    def explain_match(invoice: Invoice, transaction: BankTransaction, score: Decimal) -> str:
        """Generate AI explanation for a match decision. Falls back to deterministic explanation if AI is unavailable"""
        if settings.ai_enabled and settings.openai_api_key:
            try:
                return AIService._get_ai_explanation(invoice, transaction, score)
            except Exception:
                return AIService._get_deterministic_explanation(invoice, transaction, score)
        return AIService._get_deterministic_explanation(invoice, transaction, score)

    @staticmethod
    def _get_ai_explanation(
        invoice: Invoice,
        transaction: BankTransaction,
        score: Decimal,
    ) -> str:
        """Get explanation from OpenAI API"""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)

            context = {
                "invoice": {
                    "amount": str(invoice.amount),
                    "currency": invoice.currency,
                    "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                    "invoice_number": invoice.invoice_number,
                    "description": invoice.description,
                    "vendor": invoice.vendor.name if invoice.vendor else None,
                },
                "transaction": {
                    "amount": str(transaction.amount),
                    "currency": transaction.currency,
                    "posted_at": transaction.posted_at.isoformat(),
                    "description": transaction.description,
                },
                "match_score": str(score),
            }

            prompt = f"""You are analyzing a potential match between an invoice and a bank transaction for reconciliation purposes.

Invoice:
- Amount: {context['invoice']['amount']} {context['invoice']['currency']}
- Date: {context['invoice']['invoice_date'] or 'Not provided'}
- Invoice Number: {context['invoice']['invoice_number'] or 'Not provided'}
- Description: {context['invoice']['description'] or 'Not provided'}
- Vendor: {context['invoice']['vendor'] or 'Not provided'}

Bank Transaction:
- Amount: {context['transaction']['amount']} {context['transaction']['currency']}
- Posted Date: {context['transaction']['posted_at']}
- Description: {context['transaction']['description'] or 'Not provided'}

Match Score: {context['match_score']}/100

Provide a brief explanation (2-4 sentences) of why this match was proposed and whether it appears to be a valid match. Be concise and focus on the key matching factors."""

            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a financial reconciliation assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise Exception(f"AI service failed: {str(e)}")

    @staticmethod
    def _get_deterministic_explanation(
        invoice: Invoice,
        transaction: BankTransaction,
        score: Decimal,
    ) -> str:
        """Generate deterministic explanation without AI"""
        factors = []

        # Amount analysis
        amount_diff = abs(invoice.amount - transaction.amount)
        if amount_diff == 0:
            factors.append("The amounts match exactly")
        elif amount_diff <= Decimal("0.01"):
            factors.append(f"The amounts are within 1 cent (difference: {amount_diff})")
        else:
            factors.append(f"Amount difference: {amount_diff}")

        # Date analysis
        if invoice.invoice_date and transaction.posted_at:
            date_diff = abs((invoice.invoice_date - transaction.posted_at).days)
            if date_diff == 0:
                factors.append("dates match exactly")
            elif date_diff <= 3:
                factors.append(f"dates are within {date_diff} days")
            else:
                factors.append(f"date difference: {date_diff} days")

        # Currency check
        if invoice.currency == transaction.currency:
            factors.append(f"both in {invoice.currency}")

        # Text similarity hint
        if invoice.description and transaction.description:
            if invoice.description.lower() in transaction.description.lower() or \
               transaction.description.lower() in invoice.description.lower():
                factors.append("descriptions show similarity")

        explanation = f"Match score: {score}/100. "
        if factors:
            explanation += "Factors: " + "; ".join(factors) + "."
        else:
            explanation += "Limited matching factors identified."

        return explanation
