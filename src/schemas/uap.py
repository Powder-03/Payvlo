"""Universal Agent Protocol (UAP / A2A) Schemas."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .quote import QuoteRequestItemSchema, QuoteResponseSchema
from .checkout import AddressSchema


class UAPAgentCardSchema(BaseModel):
    agent_id: str
    name: str
    description: str
    version: str
    protocol_version: str = "uap/v1"
    merchant_id: str
    merchant_name: str
    category: str
    currency: str = "INR"
    capabilities: List[str]
    endpoints: Dict[str, str]
    pricing_guardrails: Dict[str, Any]
    supported_payment_rails: List[str]


UAPAgentCardDTO = UAPAgentCardSchema


class UAPNegotiateRequestSchema(BaseModel):
    buyer_agent_id: str = Field(..., description="Identity of the buyer agent")
    intent_summary: str = Field(
        ..., description="Natural language or summary of purchase intent"
    )
    target_skus_or_ids: Optional[List[str]] = Field(
        default=None, description="Optional target SKU list"
    )
    items: Optional[List[QuoteRequestItemSchema]] = Field(
        default=None, description="Explicit item list if already known"
    )
    buyer_max_budget: float = Field(
        ..., gt=0.0, description="Authorized spending ceiling in INR"
    )
    preferred_currency: str = "INR"
    merchant_id: Optional[str] = None


UAPNegotiateRequestDTO = UAPNegotiateRequestSchema


class UAPNegotiateResponseSchema(BaseModel):
    status: str
    quote: Optional[QuoteResponseSchema]
    counter_offer_notes: str
    within_budget: bool
    requires_approval: bool
    settlement_endpoint: str = "/uap/v1/transact"


UAPNegotiateResponseDTO = UAPNegotiateResponseSchema


class UAPTransactRequestSchema(BaseModel):
    buyer_agent_id: str
    quote_id: str
    idempotency_key: str
    authorized_spend_limit: float
    shipping_address: Optional[AddressSchema] = None
    merchant_id: Optional[str] = None
    agent_signature: Optional[str] = None


UAPTransactRequestDTO = UAPTransactRequestSchema


class UAPTransactResponseSchema(BaseModel):
    status: str
    order_id: str
    razorpay_order_id: Optional[str] = None
    payment_link: Optional[str] = None
    amount_settled: float
    currency: str = "INR"
    audit_id: str
    message: str


UAPTransactResponseDTO = UAPTransactResponseSchema
