"""Merchant Domain Entities & Value Objects."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class CatalogSyncConfig:
    """Configuration for external catalog synchronization (Shopify, Custom REST API, Direct)."""
    provider: str = "direct"  # "shopify", "custom_api", "direct", "manual"
    endpoint_url: Optional[str] = None
    access_token_masked: Optional[str] = None
    field_mapping: Dict[str, str] = field(default_factory=dict)
    auto_sync: bool = False
    sync_interval_hours: int = 24
    last_synced_at: Optional[str] = None
    sync_status: str = "IDLE"  # "IDLE", "SYNCING", "SUCCESS", "FAILED"
    error_message: Optional[str] = None
    raw_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "endpoint_url": self.endpoint_url,
            "access_token_masked": self.access_token_masked,
            "field_mapping": self.field_mapping,
            "auto_sync": self.auto_sync,
            "sync_interval_hours": self.sync_interval_hours,
            "last_synced_at": self.last_synced_at,
            "sync_status": self.sync_status,
            "error_message": self.error_message,
            "raw_config": self.raw_config,
        }


@dataclass
class MerchantProfile:
    """Configuration and guardrails for a specific merchant."""
    merchant_id: str
    merchant_name: str
    category: str
    currency: str = "INR"
    max_discount_percentage: float = 15.0
    per_tx_spend_cap: float = 10000.0
    daily_merchant_spend_cap: float = 100000.0
    allowed_payment_methods: List[str] = field(
        default_factory=lambda: ["upi", "card", "netbanking"]
    )
    support_email: str = "support@merchant.com"
    webhook_secret: Optional[str] = None
    sync_config: Optional[CatalogSyncConfig] = None
    owner_user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "category": self.category,
            "currency": self.currency,
            "max_discount_percentage": self.max_discount_percentage,
            "per_tx_spend_cap": self.per_tx_spend_cap,
            "daily_merchant_spend_cap": self.daily_merchant_spend_cap,
            "allowed_payment_methods": self.allowed_payment_methods,
            "support_email": self.support_email,
            "sync_config": self.sync_config.to_dict() if self.sync_config else None,
            "owner_user_id": self.owner_user_id,
            "metadata": self.metadata,
        }
