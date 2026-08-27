"""Audit Domain Entities."""
from dataclasses import dataclass
import hashlib
from typing import Dict, Any, Optional


@dataclass
class AuditEntry:
    """Append-only audit ledger entry with privacy protection."""
    audit_id: str
    timestamp: str
    merchant_id: str
    user_id_hash: str
    action: str  # QUOTE_GENERATED, SPEND_CHECKED, ORDER_CREATED, IDEMPOTENCY_REPLAY, etc.
    idempotency_key: Optional[str]
    quote_id: Optional[str]
    order_id: Optional[str]
    amount: float
    currency: str
    masked_pii_payload: Dict[str, Any]
    status: str  # SUCCESS, REJECTED, REPLAYED
    explainability_notes: str

    @staticmethod
    def hash_user_id(user_id: str) -> str:
        """Generates deterministic SHA-256 pseudonymized hash of user identifier."""
        return hashlib.sha256(user_id.strip().lower().encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "merchant_id": self.merchant_id,
            "user_id_hash": self.user_id_hash,
            "action": self.action,
            "idempotency_key": self.idempotency_key,
            "quote_id": self.quote_id,
            "order_id": self.order_id,
            "amount": self.amount,
            "currency": self.currency,
            "masked_pii_payload": self.masked_pii_payload,
            "status": self.status,
            "explainability_notes": self.explainability_notes,
        }
