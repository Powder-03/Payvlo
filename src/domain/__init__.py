"""Domain layer module exports (Modular Monolith Bounded Contexts)."""
from .common import current_utc_timestamp
from .auth import User, IUserRepository
from .merchant import MerchantProfile, CatalogSyncConfig, IMerchantRepository
from .catalog import Product, ICatalogRepository, ICatalogSyncProvider
from .checkout import (
    Address,
    QuoteItem,
    Quote,
    Order,
    PaymentRailResult,
    IPaymentRail,
)
from .gatekeeper import IGatekeeper
from .audit import AuditEntry, IAuditRepository
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

__all__ = [
    "Address",
    "Product",
    "MerchantProfile",
    "CatalogSyncConfig",
    "User",
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
    "ICatalogSyncProvider",
    "IUserRepository",
    "IMerchantRepository",
]
