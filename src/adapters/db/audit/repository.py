"""Audit Repository SQLAlchemy Adapter."""
import json
from typing import List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import sessionmaker
from ....domain.audit.entities import AuditEntry
from ....domain.audit.ports import IAuditRepository
from .models import AuditEntryModel


class PostgresAuditRepository(IAuditRepository):
    """Append-only audit ledger repository using SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def record_audit(self, entry: AuditEntry) -> None:
        with self.session_factory() as session:
            a = AuditEntryModel(
                audit_id=entry.audit_id,
                timestamp=entry.timestamp,
                merchant_id=entry.merchant_id,
                user_id_hash=entry.user_id_hash,
                action=entry.action,
                idempotency_key=entry.idempotency_key,
                quote_id=entry.quote_id,
                order_id=entry.order_id,
                amount=entry.amount,
                currency=entry.currency,
                masked_pii_payload_json=json.dumps(entry.masked_pii_payload),
                status=entry.status,
                explainability_notes=entry.explainability_notes,
            )
            session.add(a)
            session.commit()

    def get_audit_trail(
        self,
        merchant_id: Optional[str] = None,
        user_id_hash: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuditEntry]:
        with self.session_factory() as session:
            q = session.query(AuditEntryModel)
            if merchant_id:
                q = q.filter(AuditEntryModel.merchant_id == merchant_id)
            if user_id_hash:
                q = q.filter(AuditEntryModel.user_id_hash == user_id_hash)
            entries = q.order_by(desc(AuditEntryModel.timestamp)).limit(limit).all()

            return [
                AuditEntry(
                    audit_id=e.audit_id,
                    timestamp=e.timestamp,
                    merchant_id=e.merchant_id,
                    user_id_hash=e.user_id_hash,
                    action=e.action,
                    idempotency_key=e.idempotency_key,
                    quote_id=e.quote_id,
                    order_id=e.order_id,
                    amount=e.amount,
                    currency=e.currency,
                    masked_pii_payload=json.loads(e.masked_pii_payload_json or "{}"),
                    status=e.status,
                    explainability_notes=e.explainability_notes,
                )
                for e in entries
            ]
