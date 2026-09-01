"""Checkout and Order Settlement Schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class AddressSchema(BaseModel):
    line1: str
    line2: Optional[str] = None
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "IN"
    phone: Optional[str] = None
    email: Optional[str] = None


AddressDTO = AddressSchema


class CheckoutInputSchema(BaseModel):
    quote_id: str = Field(
        ..., description="Valid Quote ID issued by request_price_quote"
    )
    idempotency_key: str = Field(
        ..., description="Unique transaction key to prevent double billing"
    )
    user_id: str = Field(..., description="Buyer identity (user ID or agent ID)")
    max_spend_budget: float = Field(
        ..., gt=0.0, description="Authorized budget ceiling for this transaction"
    )
    shipping_address: Optional[AddressSchema] = Field(
        default=None, description="Delivery physical address"
    )
    address_label: Optional[str] = Field(
        default=None,
        description="Address shortcut from user's address book (e.g. 'Home', 'Work')",
    )
    fulfillment_type: str = Field(
        default="DELIVERY",
        description="Fulfillment type: 'DELIVERY', 'DINE_IN', or 'PICKUP'",
    )
    fulfillment_notes: Optional[str] = Field(
        default=None,
        description="Table number, landmark or delivery notes (e.g. 'Table #4')",
    )
    merchant_id: Optional[str] = Field(default=None, description="Merchant ID")


CheckoutInputDTO = CheckoutInputSchema


class CheckoutResponseSchema(BaseModel):
    order_id: str
    idempotency_key: str
    merchant_id: str
    quote_id: str
    final_amount: float
    currency: str = "INR"
    payment_rail_id: str
    payment_status: str
    payment_link: str
    audit_id: str
    is_replayed: bool = False
    explainability_notes: str
    created_at: str


CheckoutResponseDTO = CheckoutResponseSchema
