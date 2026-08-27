"""Merchant Profile, Onboarding, and Catalog Sync DTOs.

Clean Architecture layer: Application.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .catalog import DirectProductInputDTO


class CatalogSyncConfigDTO(BaseModel):
    provider: str
    endpoint_url: Optional[str] = None
    access_token: Optional[str] = None
    field_mapping: Dict[str, str] = Field(default_factory=dict)
    auto_sync: bool = False
    sync_interval_hours: int = 24
    last_synced_at: Optional[str] = None
    sync_status: str = "IDLE"
    error_message: Optional[str] = None


class MerchantProfileDTO(BaseModel):
    merchant_id: str
    merchant_name: str
    category: str
    currency: str = "INR"
    max_discount_percentage: float
    per_tx_spend_cap: float
    daily_merchant_spend_cap: float
    allowed_payment_methods: List[str]
    support_email: str
    sync_config: Optional[CatalogSyncConfigDTO] = None
    owner_user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MerchantOnboardInputDTO(BaseModel):
    merchant_id: str = Field(..., description="Unique merchant slug")
    merchant_name: str = Field(..., description="Brand or store name")
    category: str = Field(..., description="Merchant category")
    currency: str = Field(default="INR")
    max_discount_percentage: float = Field(default=15.0, ge=0.0, le=100.0)
    per_tx_spend_cap: float = Field(default=10000.0, gt=0.0)
    daily_merchant_spend_cap: float = Field(default=100000.0, gt=0.0)
    allowed_payment_methods: List[str] = Field(default_factory=lambda: ["upi", "card", "netbanking"])
    support_email: str = Field(default="support@merchant.com")
    webhook_secret: Optional[str] = None
    sync_config: Optional[CatalogSyncConfigDTO] = None
    initial_products: Optional[List[DirectProductInputDTO]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MerchantOnboardResponseDTO(BaseModel):
    success: bool
    merchant: MerchantProfileDTO
    synced_products_count: int
    agent_card_url: str
    message: str


class CatalogSyncTriggerDTO(BaseModel):
    raw_payload: Optional[List[Dict[str, Any]]] = None


class CatalogSyncResponseDTO(BaseModel):
    success: bool
    merchant_id: str
    synced_products_count: int
    provider: str
    sync_status: str
    last_synced_at: Optional[str] = None
    error_message: Optional[str] = None
    message: str


class MerchantListResponseDTO(BaseModel):
    total_merchants: int
    merchants: List[MerchantProfileDTO]
