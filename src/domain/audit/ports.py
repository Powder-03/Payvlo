"""Audit Domain Ports."""
from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import AuditEntry


class IAuditRepository(ABC):
    """Port for append-only audit ledger."""

    @abstractmethod
    def record_audit(self, entry: AuditEntry) -> None:
        """Append an audit record to the ledger."""
        pass

    @abstractmethod
    def get_audit_trail(
        self,
        merchant_id: Optional[str] = None,
        user_id_hash: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuditEntry]:
        """Fetch audit history filtered by merchant or user hash."""
        pass
