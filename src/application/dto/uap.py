"""NPCI Universal Agent Protocol (UAP / A2A) DTOs.

Clean Architecture layer: Application.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .quote import QuoteRequestItemDTO, QuoteResponseDTO
from .checkout import AddressDTO, CheckoutResponseDTO


class UAPAgentCardDTO(BaseModel):
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


class UAPNegotiateRequestDTO(BaseModel):
    buyer_agent_id: str = Field(..., description="Identity of the buyer agent")
    intent_summary: str = Field(..., description="Natural language or summary of purchase intent")
    target_skus_or_ids: Optional[List[str]] = Field(default=None, description="Optional target SKU list")
    items: Optional[List[QuoteRequestItemDTO]] = Field(default=None, description="Explicit item list if already known")
    buyer_max_budget: float = Field(..., gt=0.0, description="Authorized spending ceiling in INR")
    preferred_currency: str = "INR"
    merchant_id: Optional[str] = None


class UAPNegotiateResponseDTO(BaseModel):
    status: str
    quote: Optional[QuoteResponseDTO]
    counter_offer_notes: str
    within_budget: bool
    requires_approval: bool
    settlement_endpoint: str = "/uap/v1/transact"


class UAPTransactRequestDTO(BaseModel):
    buyer_agent_id: str
    quote_id: str
    idempotency_key: str
    authorized_budget: float
    shipping_address: Optional[AddressDTO] = None
    merchant_id: Optional[str] = None


class UAPTransactResponseDTO(BaseModel):
    status: str
    order: Optional[CheckoutResponseDTO]
    receipt_notes: str
    settled: bool
