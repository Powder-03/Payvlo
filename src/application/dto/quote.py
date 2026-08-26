"""Price Quotation and Discount Clamping DTOs.

Clean Architecture layer: Application.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class QuoteRequestItemDTO(BaseModel):
    product_id: str = Field(..., description="Target Product ID or SKU")
    quantity: int = Field(default=1, ge=1, description="Quantity requested")
    requested_discount_pct: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Requested discount percentage for this item"
    )


class QuoteRequestInputDTO(BaseModel):
    items: List[QuoteRequestItemDTO] = Field(..., min_length=1)
    overall_requested_discount_pct: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Storewide requested discount percentage"
    )
    merchant_id: Optional[str] = Field(
        default=None, description="Target merchant ID"
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
    currency: str = "INR"
    clamped_discount_reasons: List[str] = Field(default_factory=list)
    created_at: str
    expires_at: str
    status: str
    explainability: Dict[str, Any] = Field(default_factory=dict)
