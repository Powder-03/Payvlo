"""Domain layer module exports."""
from .entities import (
    Address,
    Product,
    MerchantProfile,
    QuoteItem,
    Quote,
    PaymentRailResult,
    Order,
    AuditEntry,
    current_utc_timestamp,
)
from .exceptions import (
    DomainError,
    SpendCapExceededError,
    OutOfStockError,
    ProductNotFoundError,
    QuoteExpiredError,
    PolicyViolationError,
    IdempotencyReplayError,
    PaymentRailError,
    MerchantConfigError,
)
from .ports import (
    ICatalogRepository,
    IAuditRepository,
    IGatekeeper,
    IPaymentRail,
)

__all__ = [
    "Address",
    "Product",
    "MerchantProfile",
    "QuoteItem",
    "Quote",
    "PaymentRailResult",
    "Order",
    "AuditEntry",
    "current_utc_timestamp",
    "DomainError",
    "SpendCapExceededError",
    "OutOfStockError",
    "ProductNotFoundError",
    "QuoteExpiredError",
    "PolicyViolationError",
    "IdempotencyReplayError",
    "PaymentRailError",
    "MerchantConfigError",
    "ICatalogRepository",
    "IAuditRepository",
    "IGatekeeper",
    "IPaymentRail",
]
