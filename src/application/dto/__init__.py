"""Application Layer Data Transfer Objects (DTOs) & Pydantic v2 Schemas.

Clean Architecture layer: Application.
Defines strict input/output boundaries for MCP tools, UAP/A2A endpoints, and Merchant Auth Portal.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


# ==========================================
# Catalog DTOs
# ==========================================
class ProductDTO(BaseModel):
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


class CatalogSearchInputDTO(BaseModel):
    query: Optional[str] = Field(
        default=None, description="Keywords to match in title, description, or tags"
    )
    category: Optional[str] = Field(
        default=None, description="Filter products by merchant category (e.g. 'Pizzas', 'Supplements')"
    )
    min_price: Optional[float] = Field(
        default=None, description="Minimum price in INR"
    )
    max_price: Optional[float] = Field(
        default=None, description="Maximum price in INR"
    )
    merchant_id: Optional[str] = Field(
        default=None, description="Specific merchant ID or omit to use active merchant"
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class CatalogSearchResultDTO(BaseModel):
    merchant_id: str
    total_count: int
    products: List[ProductDTO]


# ==========================================
# Quote DTOs
# ==========================================
class QuoteRequestItemDTO(BaseModel):
    product_id: str = Field(..., description="Unique product ID or SKU")
    quantity: int = Field(default=1, ge=1, description="Quantity to purchase")
    requested_discount_pct: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Requested discount percentage for this specific item"
    )


class QuoteRequestInputDTO(BaseModel):
    items: List[QuoteRequestItemDTO] = Field(
        ..., min_length=1, description="List of items for quotation"
    )
    overall_requested_discount_pct: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Overall coupon or negotiation discount"
    )
    merchant_id: Optional[str] = Field(
        default=None, description="Specific merchant ID for quotation"
    )


class QuoteItemDTO(BaseModel):
    product_id: str
    sku: str
    title: str
    quantity: int
    unit_price: float
    requested_discount_pct: float
    effective_discount_pct: float
    discount_amount: float
    subtotal: float
    final_price: float
    clamping_reason: Optional[str] = None


class QuoteResponseDTO(BaseModel):
    quote_id: str
    merchant_id: str
    items: List[QuoteItemDTO]
    total_original_price: float
    total_discount_amount: float
    final_total_price: float
    currency: str
    clamped_discount_reasons: List[str]
    created_at: str
    expires_at: str
    status: str


# ==========================================
# Checkout & Order DTOs
# ==========================================
class AddressDTO(BaseModel):
    line1: str = Field(..., description="Street address line 1")
    line2: Optional[str] = None
    city: str = Field(default="", description="City")
    state: str = Field(default="", description="State / Province")
    postal_code: str = Field(default="", description="Postal / ZIP code")
    country: str = Field(default="IN", description="ISO Country code")
    phone: Optional[str] = Field(default=None, description="Contact phone number")
    email: Optional[str] = Field(default=None, description="Contact email address")


class CheckoutInputDTO(BaseModel):
    quote_id: str = Field(..., description="Active Quote ID generated from quote request")
    idempotency_key: str = Field(
        ..., description="Unique client-generated idempotency key (valid for 24h)"
    )
    user_id: str = Field(..., description="Buyer or Agent identifier")
    max_spend_budget: float = Field(
        ..., gt=0.0, description="Strict maximum authorized spend limit"
    )
    shipping_address: Optional[AddressDTO] = Field(
        default=None, description="Shipping destination address"
    )
    merchant_id: Optional[str] = Field(
        default=None, description="Specific merchant ID for checkout"
    )


class CheckoutResponseDTO(BaseModel):
    order_id: str
    idempotency_key: str
    merchant_id: str
    quote_id: str
    final_amount: float
    currency: str
    payment_rail_id: str
    payment_status: str
    payment_link: str
    audit_id: str
    is_replayed: bool = False
    explainability_notes: str
    created_at: str


# ==========================================
# Audit DTOs
# ==========================================
class AuditInspectInputDTO(BaseModel):
    merchant_id: Optional[str] = Field(default=None, description="Filter by merchant ID")
    user_id: Optional[str] = Field(default=None, description="Filter by buyer identifier")
    limit: int = Field(default=50, ge=1, le=200, description="Max audit records to return")


class AuditEntryDTO(BaseModel):
    audit_id: str
    timestamp: str
    merchant_id: str
    user_id_hash: str
    action: str
    idempotency_key: Optional[str]
    quote_id: Optional[str]
    order_id: Optional[str]
    amount: float
    currency: str
    masked_pii_payload: Dict[str, Any]
    status: str
    explainability_notes: str


class AuditInspectResponseDTO(BaseModel):
    total_entries: int
    entries: List[AuditEntryDTO]


# ==========================================
# Universal Agent Protocol (UAP) DTOs
# ==========================================
class UAPAgentCardDTO(BaseModel):
    name: str
    merchant_id: str
    merchant_name: str
    category: str
    currency: str
    capabilities: List[str]
    endpoints: Dict[str, str]
    pricing_guardrails: Dict[str, Any]
    supported_payment_rails: List[str]


class UAPNegotiateRequestDTO(BaseModel):
    buyer_agent_id: str = Field(..., description="Identity of the buyer agent")
    intent_summary: str = Field(..., description="Natural language purchase intent")
    target_skus_or_ids: Optional[List[str]] = Field(
        default=None, description="Target product IDs or SKUs"
    )
    items: Optional[List[QuoteRequestItemDTO]] = Field(
        default=None, description="Specific items and quantities"
    )
    buyer_max_budget: float = Field(
        ..., gt=0.0, description="Maximum budget authorized by buyer agent"
    )
    merchant_id: Optional[str] = Field(default=None)


class UAPNegotiateResponseDTO(BaseModel):
    status: str  # OFFERED, COUNTER_OFFER, REJECTED
    quote: Optional[QuoteResponseDTO] = None
    counter_offer_notes: str
    within_budget: bool
    requires_approval: bool = False
    settlement_endpoint: str


class UAPTransactRequestDTO(BaseModel):
    buyer_agent_id: str = Field(..., description="Identity of the buyer agent")
    quote_id: str = Field(..., description="Agreed Quote ID")
    idempotency_key: str = Field(..., description="Client idempotency key")
    authorized_spend_limit: float = Field(..., gt=0.0)
    shipping_address: Optional[AddressDTO] = None
    agent_signature: Optional[str] = Field(
        default=None, description="Cryptographic signature from buyer agent"
    )
    merchant_id: Optional[str] = None


class UAPTransactResponseDTO(BaseModel):
    status: str  # SETTLED, PENDING_PAYMENT, REJECTED, REPLAYED
    order_id: str
    razorpay_order_id: str
    payment_link: str
    amount_settled: float
    currency: str
    audit_id: str
    message: str


# ==========================================
# Merchant Onboarding & Catalog Sync DTOs
# ==========================================
class CatalogSyncConfigDTO(BaseModel):
    provider: str = Field(default="direct", description="'shopify', 'custom_api', 'direct', or 'manual'")
    endpoint_url: Optional[str] = Field(default=None, description="Remote API URL or Shopify store URL")
    access_token: Optional[str] = Field(default=None, description="API Access token or Shopify private token")
    field_mapping: Dict[str, str] = Field(default_factory=dict, description="Custom JSON field mappings")
    auto_sync: bool = Field(default=False, description="Enable periodic auto-sync")
    sync_interval_hours: int = Field(default=24, ge=1, le=168)
    last_synced_at: Optional[str] = None
    sync_status: str = "IDLE"
    error_message: Optional[str] = None


class DirectProductInputDTO(BaseModel):
    product_id: Optional[str] = None
    sku: str = Field(..., description="Unique SKU code")
    title: str = Field(..., description="Product title")
    description: str = Field(default="")
    price_inr: float = Field(..., gt=0.0, description="Price in INR")
    inventory_count: int = Field(default=10, ge=0, description="Available stock")
    category: str = Field(default="General")
    max_discount_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MerchantOnboardInputDTO(BaseModel):
    merchant_id: str = Field(..., min_length=2, max_length=64, description="Unique slug for merchant")
    merchant_name: str = Field(..., min_length=2, description="Display brand / merchant name")
    category: str = Field(..., description="Store business category")
    currency: str = Field(default="INR", max_length=10)
    max_discount_percentage: float = Field(default=15.0, ge=0.0, le=100.0, description="Hard merchant discount ceiling")
    per_tx_spend_cap: float = Field(default=10000.0, gt=0.0, description="Max single transaction limit in INR")
    daily_merchant_spend_cap: float = Field(default=100000.0, gt=0.0, description="Max 24h daily spend across node in INR")
    allowed_payment_methods: List[str] = Field(
        default_factory=lambda: ["upi", "card", "netbanking"]
    )
    support_email: str = Field(default="support@merchant.com")
    webhook_secret: Optional[str] = None
    sync_config: Optional[CatalogSyncConfigDTO] = None
    initial_products: Optional[List[DirectProductInputDTO]] = Field(
        default=None, description="Optional initial list of products to seed immediately"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MerchantProfileDTO(BaseModel):
    merchant_id: str
    merchant_name: str
    category: str
    currency: str
    max_discount_percentage: float
    per_tx_spend_cap: float
    daily_merchant_spend_cap: float
    allowed_payment_methods: List[str]
    support_email: str
    sync_config: Optional[CatalogSyncConfigDTO] = None
    owner_user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MerchantOnboardResponseDTO(BaseModel):
    success: bool
    merchant: MerchantProfileDTO
    synced_products_count: int
    agent_card_url: str
    message: str


class CatalogSyncTriggerDTO(BaseModel):
    raw_payload: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Optional raw JSON product list to sync directly"
    )


class CatalogSyncResponseDTO(BaseModel):
    success: bool
    merchant_id: str
    synced_products_count: int
    provider: str
    sync_status: str
    last_synced_at: str
    error_message: Optional[str] = None
    message: str


class MerchantListResponseDTO(BaseModel):
    total_merchants: int
    merchants: List[MerchantProfileDTO]


# ==========================================
# Authentication & SaaS Portal DTOs
# ==========================================
class UserSignupInputDTO(BaseModel):
    email: str = Field(..., description="Business / Merchant email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    full_name: str = Field(default="", description="Account owner full name")
    company_name: str = Field(default="", description="Company / Brand name")


class UserLoginInputDTO(BaseModel):
    email: str = Field(..., description="Registered account email")
    password: str = Field(..., description="Account password")


class UserProfileDTO(BaseModel):
    user_id: str
    email: str
    full_name: str
    company_name: str
    created_at: str


class UserAuthResponseDTO(BaseModel):
    success: bool
    token: str
    token_type: str = "bearer"
    user: UserProfileDTO
    has_store: bool = False
    merchant_id: Optional[str] = None
    message: str


class MyStoreResponseDTO(BaseModel):
    has_store: bool
    merchant: Optional[MerchantProfileDTO] = None
    total_products: int = 0
    agent_card_url: Optional[str] = None
    products: List[ProductDTO] = Field(default_factory=list)


__all__ = [
    "ProductDTO",
    "CatalogSearchInputDTO",
    "CatalogSearchResultDTO",
    "QuoteRequestItemDTO",
    "QuoteRequestInputDTO",
    "QuoteItemDTO",
    "QuoteResponseDTO",
    "AddressDTO",
    "CheckoutInputDTO",
    "CheckoutResponseDTO",
    "AuditInspectInputDTO",
    "AuditEntryDTO",
    "AuditInspectResponseDTO",
    "UAPAgentCardDTO",
    "UAPNegotiateRequestDTO",
    "UAPNegotiateResponseDTO",
    "UAPTransactRequestDTO",
    "UAPTransactResponseDTO",
    "CatalogSyncConfigDTO",
    "DirectProductInputDTO",
    "MerchantOnboardInputDTO",
    "MerchantProfileDTO",
    "MerchantOnboardResponseDTO",
    "CatalogSyncTriggerDTO",
    "CatalogSyncResponseDTO",
    "MerchantListResponseDTO",
    "UserSignupInputDTO",
    "UserLoginInputDTO",
    "UserProfileDTO",
    "UserAuthResponseDTO",
    "MyStoreResponseDTO",
]
