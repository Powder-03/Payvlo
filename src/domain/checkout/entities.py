"""Checkout, Quotes, Orders, Address & Payment Domain Entities."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from ..common.timestamps import current_utc_timestamp


@dataclass(frozen=True)
class Address:
    """Represents a shipping / billing physical address."""
    line1: str
    line2: Optional[str] = None
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "IN"
    phone: Optional[str] = None
    email: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Returns full address dictionary for order fulfillment."""
        return {
            "line1": self.line1,
            "line2": self.line2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "phone": self.phone,
            "email": self.email,
        }

    def to_masked_dict(self) -> Dict[str, Any]:
        """Returns privacy-preserving masked address dictionary for audit logs."""
        masked_phone = None
        if self.phone:
            digits = "".join(filter(str.isdigit, self.phone))
            if len(digits) >= 4:
                masked_phone = f"+91-XXXXX-{digits[-4:]}"
            else:
                masked_phone = "XXXX"

        masked_email = None
        if self.email and "@" in self.email:
            name, domain = self.email.split("@", 1)
            prefix = name[:2] if len(name) >= 2 else name[:1]
            masked_email = f"{prefix}***@{domain}"

        masked_line1 = f"***, {self.city}" if self.city else "***"

        return {
            "masked_line1": masked_line1,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "masked_phone": masked_phone,
            "masked_email": masked_email,
        }



@dataclass
class QuoteItem:
    """Line item in a bound price quote."""
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "sku": self.sku,
            "title": self.title,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "requested_discount_pct": self.requested_discount_pct,
            "effective_discount_pct": self.effective_discount_pct,
            "discount_amount": self.discount_amount,
            "subtotal": self.subtotal,
            "final_price": self.final_price,
            "clamping_reason": self.clamping_reason,
        }


@dataclass
class Quote:
    """Cryptographically or temporally bound quotation ready for execution."""
    quote_id: str
    merchant_id: str
    items: List[QuoteItem]
    total_original_price: float
    total_discount_amount: float
    final_total_price: float
    currency: str = "INR"
    clamped_discount_reasons: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=current_utc_timestamp)
    expires_at: str = ""
    status: str = "ACTIVE"  # ACTIVE, CONSUMED, EXPIRED

    def is_expired(self) -> bool:
        """Evaluates whether the quote timestamp has lapsed."""
        if not self.expires_at:
            return False
        try:
            exp_time = datetime.fromisoformat(self.expires_at)
            return datetime.now(timezone.utc) > exp_time
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quote_id": self.quote_id,
            "merchant_id": self.merchant_id,
            "items": [item.to_dict() for item in self.items],
            "total_original_price": self.total_original_price,
            "total_discount_amount": self.total_discount_amount,
            "final_total_price": self.final_total_price,
            "currency": self.currency,
            "clamped_discount_reasons": self.clamped_discount_reasons,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
        }


@dataclass
class PaymentRailResult:
    """Result of creating or executing an order on a payment rail (e.g. Razorpay)."""
    rail_order_id: str
    payment_link: str
    status: str
    amount_in_subunit: int  # in paise / cents (e.g., 50000 = ₹500.00)
    currency: str
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rail_order_id": self.rail_order_id,
            "payment_link": self.payment_link,
            "status": self.status,
            "amount_in_subunit": self.amount_in_subunit,
            "currency": self.currency,
            "raw_response": self.raw_response,
        }


@dataclass
class Order:
    """Final settled or created commerce order."""
    order_id: str
    idempotency_key: str
    merchant_id: str
    user_id: str
    quote_id: str
    items: List[QuoteItem]
    final_amount: float
    currency: str
    shipping_address: Optional[Address]
    payment_rail_id: str
    payment_status: str
    payment_link: str
    audit_id: str
    created_at: str = field(default_factory=current_utc_timestamp)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "idempotency_key": self.idempotency_key,
            "merchant_id": self.merchant_id,
            "user_id": self.user_id,
            "quote_id": self.quote_id,
            "items": [item.to_dict() for item in self.items],
            "final_amount": self.final_amount,
            "currency": self.currency,
            "shipping_address": self.shipping_address.to_masked_dict() if self.shipping_address else None,
            "payment_rail_id": self.payment_rail_id,
            "payment_status": self.payment_status,
            "payment_link": self.payment_link,
            "audit_id": self.audit_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }
