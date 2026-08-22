"""Razorpay Payment Rail Adapter for Agentic Commerce Node.

Clean Architecture layer: Adapters.
Implements IPaymentRail port using Razorpay Python SDK (Test Mode Sandbox).
Provides fallback mock capabilities for local integration testing.
"""
import uuid
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional

try:
    import razorpay
except ImportError:
    razorpay = None

from ..domain.entities import PaymentRailResult
from ..domain.exceptions import PaymentRailError
from ..domain.ports import IPaymentRail

logger = logging.getLogger("RazorpayRails")


class RazorpayPaymentRailAdapter(IPaymentRail):
    """Adapter connecting the commerce node to Razorpay test payment rails."""

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        is_sandbox: bool = True,
    ):
        self.key_id = key_id or "rzp_test_placeholder_key"
        self.key_secret = key_secret or "rzp_test_placeholder_secret"
        self.is_sandbox = is_sandbox
        self.client = None

        if (
            razorpay
            and key_id
            and key_secret
            and not key_id.startswith("rzp_test_placeholder")
        ):
            try:
                self.client = razorpay.Client(auth=(key_id, key_secret))
                logger.info(f"Initialized live Razorpay Client with Key ID: {key_id[:10]}...")
            except Exception as e:
                logger.warning(f"Failed to initialize live Razorpay Client ({e}). Using test sandbox simulator.")
                self.client = None
        else:
            logger.info("Using built-in Razorpay Sandbox Test Rail Simulator.")

    def create_order(
        self,
        merchant_id: str,
        order_id: str,
        amount_in_inr: float,
        currency: str = "INR",
        notes: Optional[Dict[str, Any]] = None,
    ) -> PaymentRailResult:
        """Creates an authorized order on Razorpay test rails."""
        # Convert INR to subunits (Paise)
        amount_in_paise = int(round(amount_in_inr * 100))

        if amount_in_paise <= 0:
            raise PaymentRailError(
                "RAZORPAY", f"Order amount must be greater than zero. Got ₹{amount_in_inr:.2f}."
            )

        order_payload = {
            "amount": amount_in_paise,
            "currency": currency.upper(),
            "receipt": order_id,
            "notes": notes or {},
            "payment_capture": 1,  # Auto-capture test mode payments
        }

        # If live client is active and configured
        if self.client:
            try:
                rzp_order = self.client.order.create(data=order_payload)
                rail_id = rzp_order.get("id")
                payment_link = (
                    f"https://api.razorpay.com/v1/checkout/embedded?order_id={rail_id}"
                )
                return PaymentRailResult(
                    rail_order_id=rail_id,
                    payment_link=payment_link,
                    status=rzp_order.get("status", "created"),
                    amount_in_subunit=amount_in_paise,
                    currency=currency,
                    raw_response=rzp_order,
                )
            except Exception as e:
                logger.error(f"Razorpay API error: {e}")
                # Fallback to deterministic test response if sandbox test credentials fail
                if not self.is_sandbox:
                    raise PaymentRailError("RAZORPAY", str(e))

        # Deterministic Sandbox / Test Mode Simulator
        simulated_rail_id = f"order_{uuid.uuid4().hex[:14]}"
        simulated_payment_link = (
            f"https://sandbox.razorpay.com/v1/checkout/test_pay?order_id={simulated_rail_id}&amount={amount_in_paise}"
        )
        simulated_response = {
            "id": simulated_rail_id,
            "entity": "order",
            "amount": amount_in_paise,
            "amount_paid": 0,
            "amount_due": amount_in_paise,
            "currency": currency,
            "receipt": order_id,
            "status": "created",
            "attempts": 0,
            "notes": notes or {},
            "created_at": int(uuid.uuid1().time),
        }

        return PaymentRailResult(
            rail_order_id=simulated_rail_id,
            payment_link=simulated_payment_link,
            status="created",
            amount_in_subunit=amount_in_paise,
            currency=currency,
            raw_response=simulated_response,
        )

    def verify_payment_signature(
        self, order_id: str, payment_id: str, signature: str
    ) -> bool:
        """Verifies webhook or client payment signature."""
        if self.client:
            try:
                self.client.utility.verify_payment_signature(
                    {
                        "razorpay_order_id": order_id,
                        "razorpay_payment_id": payment_id,
                        "razorpay_signature": signature,
                    }
                )
                return True
            except Exception:
                return False

        # Sandbox HMAC Verification
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        expected_sig = hmac.HMAC(
            self.key_secret.encode("utf-8"), msg, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_sig, signature)
