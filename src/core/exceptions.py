"""Application and Domain Exceptions."""
from typing import Optional, Dict, Any


class DomainError(Exception):
    """Base exception for all business logic and domain errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class SpendCapExceededError(DomainError):
    """Raised when an attempted transaction exceeds user-defined budget or merchant limits."""

    def __init__(
        self,
        attempted_amount: float,
        limit_amount: float,
        limit_type: str,
        message: Optional[str] = None,
    ):
        msg = message or (
            f"Spend cap exceeded: Attempted amount ₹{attempted_amount:.2f} exceeds "
            f"{limit_type} limit of ₹{limit_amount:.2f}."
        )
        details = {
            "attempted_amount": attempted_amount,
            "limit_amount": limit_amount,
            "limit_type": limit_type,
        }
        super().__init__(msg, details)


class OutOfStockError(DomainError):
    """Raised when requested product inventory is insufficient."""

    def __init__(self, product_id: str, requested: int, available: int):
        msg = (
            f"Insufficient inventory for product '{product_id}': "
            f"Requested {requested}, but only {available} available."
        )
        details = {
            "product_id": product_id,
            "requested_quantity": requested,
            "available_quantity": available,
        }
        super().__init__(msg, details)


class ProductNotFoundError(DomainError):
    """Raised when a requested product does not exist in catalog."""

    def __init__(self, product_id: str, merchant_id: Optional[str] = None):
        msg = f"Product '{product_id}' not found in catalog for merchant '{merchant_id or 'default'}'."
        details = {"product_id": product_id, "merchant_id": merchant_id}
        super().__init__(msg, details)


class QuoteExpiredError(DomainError):
    """Raised when an expired quote token is submitted for checkout."""

    def __init__(self, quote_id: str, expired_at: str):
        msg = f"Price quote '{quote_id}' expired at {expired_at}. Please request a fresh quote."
        details = {"quote_id": quote_id, "expired_at": expired_at}
        super().__init__(msg, details)


class PolicyViolationError(DomainError):
    """Raised when a merchant policy or discount constraint is violated."""

    def __init__(self, rule_name: str, message: str, context: Optional[Dict[str, Any]] = None):
        msg = f"Policy violation [{rule_name}]: {message}"
        details = {"rule_name": rule_name, **(context or {})}
        super().__init__(msg, details)


class IdempotencyReplayError(DomainError):
    """Raised or used to signal a replayed idempotent transaction."""

    def __init__(self, idempotency_key: str, existing_order_id: str, message: Optional[str] = None):
        msg = message or f"Idempotency key '{idempotency_key}' was already processed with order '{existing_order_id}'."
        details = {
            "idempotency_key": idempotency_key,
            "existing_order_id": existing_order_id,
        }
        super().__init__(msg, details)


class PaymentRailError(DomainError):
    """Raised when the underlying payment rail (e.g. Razorpay) fails or rejects an order."""

    def __init__(self, rail_name: str, message: str, rail_error_code: Optional[str] = None):
        msg = f"Payment rail [{rail_name}] error: {message}"
        details = {"rail_name": rail_name, "rail_error_code": rail_error_code}
        super().__init__(msg, details)


class MerchantConfigError(DomainError):
    """Raised when merchant configuration is missing or invalid."""

    def __init__(self, merchant_id: str, reason: str):
        msg = f"Merchant configuration error for '{merchant_id}': {reason}"
        details = {"merchant_id": merchant_id, "reason": reason}
        super().__init__(msg, details)
