"""Checkout & Payment Domain Ports."""
from abc import ABC, abstractmethod
from typing import Dict, Any
from .entities import PaymentRailResult


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
