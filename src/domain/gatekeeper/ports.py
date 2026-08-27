"""Gatekeeper Domain Ports."""
from abc import ABC, abstractmethod
from typing import Optional, Tuple


class IGatekeeper(ABC):
    """Port for atomic spend caps, budget bounds, and idempotency locks (Upstash Redis)."""

    @abstractmethod
    def check_and_acquire_idempotency(
        self, idempotency_key: str, payload: str, ttl_seconds: int = 86400
    ) -> Tuple[bool, Optional[str]]:
        """Atomically check and acquire idempotency key for 24h.

        Returns (is_new, cached_payload).
        """
        pass

    @abstractmethod
    def check_and_record_spend(
        self,
        merchant_id: str,
        user_id: str,
        amount: float,
        user_budget: float,
        merchant_cap: float,
    ) -> Tuple[bool, str, float, float]:
        """Atomically check whether transaction is within user budget and merchant daily cap.

        Returns (is_approved, reason_or_status, current_user_spend, current_merchant_spend).
        """
        pass

    @abstractmethod
    def release_spend(
        self, merchant_id: str, user_id: str, amount: float
    ) -> None:
        """Release reserved spend in case of downstream failure."""
        pass
