"""Privacy-Preserving Audit Trail Service."""
import uuid
import json
import time
import hashlib
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import sessionmaker

from ..models.audit import AuditEntryModel
from ..schemas.audit import AuditEntrySchema, AuditInspectInputSchema, AuditInspectResponseSchema


def hash_user_id(user_id: str) -> str:
    """Generates deterministic SHA-256 pseudonymized hash of user identifier."""
    return hashlib.sha256(user_id.strip().lower().encode("utf-8")).hexdigest()[:16]


def mask_shipping_address(addr: Optional[Any]) -> Dict[str, Any]:
    """Returns privacy-preserving masked address dictionary for audit logs."""
    if not addr:
        return {}

    # Support dict or object with attributes
    line1 = getattr(addr, "line1", None) or (addr.get("line1") if isinstance(addr, dict) else "")
    city = getattr(addr, "city", None) or (addr.get("city") if isinstance(addr, dict) else "")
    state = getattr(addr, "state", None) or (addr.get("state") if isinstance(addr, dict) else "")
    postal_code = getattr(addr, "postal_code", None) or (addr.get("postal_code") if isinstance(addr, dict) else "")
    country = getattr(addr, "country", None) or (addr.get("country", "IN") if isinstance(addr, dict) else "IN")
    phone = getattr(addr, "phone", None) or (addr.get("phone") if isinstance(addr, dict) else None)
    email = getattr(addr, "email", None) or (addr.get("email") if isinstance(addr, dict) else None)

    masked_phone = None
    if phone:
        digits = "".join(filter(str.isdigit, str(phone)))
        if len(digits) >= 4:
            masked_phone = f"+91-XXXXX-{digits[-4:]}"
        else:
            masked_phone = "XXXX"

    masked_email = None
    if email and "@" in str(email):
        name, domain = str(email).split("@", 1)
        prefix = name[:2] if len(name) >= 2 else name[:1]
        masked_email = f"{prefix}***@{domain}"

    masked_line1 = f"***, {city}" if city else "***"

    return {
        "masked_line1": masked_line1,
        "city": city,
        "state": state,
        "postal_code": postal_code,
        "country": country,
        "masked_phone": masked_phone,
        "masked_email": masked_email,
    }


class AuditService:
    """Records and inspects immutable, privacy-masked audit entries."""

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def record_audit(
        self,
        merchant_id: str,
        user_id_hash: str,
        action: str,
        status: str,
        explainability_notes: str,
        idempotency_key: Optional[str] = None,
        quote_id: Optional[str] = None,
        order_id: Optional[str] = None,
        amount: float = 0.0,
        currency: str = "INR",
        masked_pii_payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Appends an immutable audit entry."""
        audit_id = f"aud_{uuid.uuid4().hex[:12]}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        with self.session_factory() as session:
            entry = AuditEntryModel(
                audit_id=audit_id,
                timestamp=timestamp,
                merchant_id=merchant_id,
                user_id_hash=user_id_hash,
                action=action,
                idempotency_key=idempotency_key,
                quote_id=quote_id,
                order_id=order_id,
                amount=amount,
                currency=currency,
                masked_pii_payload_json=json.dumps(masked_pii_payload or {}),
                status=status,
                explainability_notes=explainability_notes,
            )
            session.add(entry)
            session.commit()

        return audit_id

    def inspect_audit_trail(
        self, query: AuditInspectInputSchema
    ) -> AuditInspectResponseSchema:
        """Queries audit entries with optional merchant/user filters."""
        with self.session_factory() as session:
            q = session.query(AuditEntryModel)
            if query.merchant_id:
                q = q.filter(AuditEntryModel.merchant_id == query.merchant_id)
            if query.user_id:
                u_hash = hash_user_id(query.user_id)
                q = q.filter(AuditEntryModel.user_id_hash == u_hash)

            total = q.count()
            rows = (
                q.order_by(AuditEntryModel.timestamp.desc())
                .limit(query.limit)
                .all()
            )

            entries = [
                AuditEntrySchema(
                    audit_id=r.audit_id,
                    timestamp=r.timestamp,
                    merchant_id=r.merchant_id,
                    user_id_hash=r.user_id_hash,
                    action=r.action,
                    idempotency_key=r.idempotency_key,
                    quote_id=r.quote_id,
                    order_id=r.order_id,
                    amount=r.amount,
                    currency=r.currency,
                    masked_pii_payload=json.loads(r.masked_pii_payload_json or "{}"),
                    status=r.status,
                    explainability_notes=r.explainability_notes or "",
                )
                for r in rows
            ]

            return AuditInspectResponseSchema(total_entries=total, entries=entries)
