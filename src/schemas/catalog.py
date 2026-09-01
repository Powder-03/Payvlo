"""Catalog, Product, and Merchant Schemas."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class ProductSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    merchant_id: str
    sku: str
    title: str
    description: str
    price_inr: float
    inventory_count: int
    category: str
    max_discount_percentage: float = 0.0
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Backward-compatible alias
ProductDTO = ProductSchema


class CatalogSearchInputSchema(BaseModel):
    query: Optional[str] = Field(
        default=None, description="Keywords to match in title, description, or tags"
    )
    category: Optional[str] = Field(
        default=None, description="Filter products by merchant category"
    )
    min_price: Optional[float] = Field(
        default=None, description="Minimum price in INR"
    )
    max_price: Optional[float] = Field(
        default=None, description="Maximum price in INR"
    )
    merchant_id: Optional[str] = Field(
        default=None, description="Specific merchant ID"
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


CatalogSearchInputDTO = CatalogSearchInputSchema


class CatalogSearchResultSchema(BaseModel):
    merchant_id: str
    total_count: int
    products: List[ProductSchema]


CatalogSearchResultDTO = CatalogSearchResultSchema


class DirectProductInputSchema(BaseModel):
    sku: str
    title: str
    description: Optional[str] = ""
    price_inr: float = Field(..., gt=0.0)
    inventory_count: int = Field(default=10, ge=0)
    category: str = "General"
    max_discount_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


DirectProductInputDTO = DirectProductInputSchema


class CatalogSyncConfigSchema(BaseModel):
    provider: str
    endpoint_url: Optional[str] = None
    access_token: Optional[str] = None
    field_mapping: Dict[str, str] = Field(default_factory=dict)
    auto_sync: bool = False
    sync_interval_hours: int = 24
    last_synced_at: Optional[str] = None
    sync_status: str = "IDLE"
    error_message: Optional[str] = None


CatalogSyncConfigDTO = CatalogSyncConfigSchema


class MerchantProfileSchema(BaseModel):
    merchant_id: str
    merchant_name: str
    category: str
    currency: str = "INR"
    max_discount_percentage: float
    per_tx_spend_cap: float
    daily_merchant_spend_cap: float
    allowed_payment_methods: List[str]
    support_email: str
    sync_config: Optional[CatalogSyncConfigSchema] = None
    owner_user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


MerchantProfileDTO = MerchantProfileSchema


class MerchantOnboardInputSchema(BaseModel):
    merchant_id: str = Field(..., description="Unique merchant slug")
    merchant_name: str = Field(..., description="Brand or store name")
    category: str = Field(..., description="Merchant category")
    currency: str = Field(default="INR")
    max_discount_percentage: float = Field(default=15.0, ge=0.0, le=100.0)
    per_tx_spend_cap: float = Field(default=10000.0, gt=0.0)
    daily_merchant_spend_cap: float = Field(default=100000.0, gt=0.0)
    allowed_payment_methods: List[str] = Field(
        default_factory=lambda: ["upi", "card", "netbanking"]
    )
    support_email: str = Field(default="support@merchant.com")
    webhook_secret: Optional[str] = None
    sync_config: Optional[CatalogSyncConfigSchema] = None
    initial_products: Optional[List[DirectProductInputSchema]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


MerchantOnboardInputDTO = MerchantOnboardInputSchema


class MerchantOnboardResponseSchema(BaseModel):
    success: bool
    merchant: MerchantProfileSchema
    synced_products_count: int
    agent_card_url: str
    message: str


MerchantOnboardResponseDTO = MerchantOnboardResponseSchema


class CatalogSyncTriggerSchema(BaseModel):
    raw_payload: Optional[List[Dict[str, Any]]] = None


CatalogSyncTriggerDTO = CatalogSyncTriggerSchema


class CatalogSyncResponseSchema(BaseModel):
    success: bool
    merchant_id: str
    synced_products_count: int
    provider: str
    sync_status: str
    last_synced_at: Optional[str] = None
    error_message: Optional[str] = None
    message: str


CatalogSyncResponseDTO = CatalogSyncResponseSchema


class MerchantListResponseSchema(BaseModel):
    total_merchants: int
    merchants: List[MerchantProfileSchema]


MerchantListResponseDTO = MerchantListResponseSchema
