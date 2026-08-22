"""Enterprise Domain Ports (Interfaces / Contracts) for Agentic Commerce Node.

Pure Python abstract base classes defining egress interfaces.
Clean Architecture layer: Domain.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from .entities import (
    Product,
    MerchantProfile,
    Quote,
    Order,
    AuditEntry,
    PaymentRailResult,
)


class ICatalogRepository(ABC):
    """Port for catalog, inventory, and order persistence."""

    @abstractmethod
    def get_merchant(self, merchant_id: str) -> Optional[MerchantProfile]:
        """Fetch merchant profile and spending rules."""
        pass

    @abstractmethod
    def save_merchant(self, merchant: MerchantProfile) -> None:
        """Upsert merchant profile."""
        pass

    @abstractmethod
    def get_product(self, merchant_id: str, product_id: str) -> Optional[Product]:
        """Retrieve single product by ID."""
        pass

    @abstractmethod
    def search_products(
        self,
        merchant_id: Optional[str] = None,
        query: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Product]:
        """Search and filter products across merchant catalog."""
        pass

    @abstractmethod
    def update_inventory(
        self, merchant_id: str, product_id: str, quantity_delta: int
    ) -> Product:
        """Atomically deduct or restore inventory for a product."""
        pass

    @abstractmethod
    def save_quote(self, quote: Quote) -> None:
        """Persist generated price quote."""
        pass

    @abstractmethod
    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Retrieve price quote by ID."""
        pass

    @abstractmethod
    def save_order(self, order: Order) -> None:
        """Persist settled order."""
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """Retrieve order by order ID."""
        pass

    @abstractmethod
    def get_order_by_idempotency(self, idempotency_key: str) -> Optional[Order]:
        """Retrieve previously processed order by idempotency key."""
        pass


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


class IPaymentRail(ABC):
    """Port for external financial rails (Razorpay test sandbox)."""

    @abstractmethod
    def create_order(
        self,
        merchant_id: str,
        order_id: str,
        amount_in_inr: float,
        currency: str,
        notes: Dict[str, Any],
    ) -> PaymentRailResult:
        """Create a trackable checkout order on the payment rail."""
        pass

    @abstractmethod
    def verify_payment_signature(
        self, order_id: str, payment_id: str, signature: str
    ) -> bool:
        """Verify webhook or callback signature."""
        pass
