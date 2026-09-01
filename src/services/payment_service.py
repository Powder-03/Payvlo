"""Payment Processing Service (Razorpay Rails & Sandbox Simulator)."""
import uuid
import logging
from typing import Dict, Any, Optional

try:
    import razorpay
except ImportError:
    razorpay = None

from ..core.exceptions import PaymentRailError

logger = logging.getLogger("PaymentService")


class PaymentService:
    """Service connecting Payvlo to Razorpay payment rails."""

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
    ) -> Dict[str, Any]:
        """Creates an authorized order on Razorpay test rails."""
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
            "payment_capture": 1,
        }

        # If live client is active
        if self.client:
            try:
                rzp_order = self.client.order.create(data=order_payload)
                rail_id = rzp_order.get("id")
                payment_link = (
                    f"https://api.razorpay.com/v1/checkout/embedded?order_id={rail_id}"
                )
                return {
                    "payment_rail_id": rail_id,
                    "payment_link": payment_link,
                    "payment_status": rzp_order.get("status", "created"),
                    "amount_in_subunit": amount_in_paise,
                    "currency": currency,
                    "raw_response": rzp_order,
                }
            except Exception as e:
                logger.error(f"Razorpay API error: {e}")
                if not self.is_sandbox:
                    raise PaymentRailError("RAZORPAY", str(e))

        # Deterministic Sandbox / Test Mode Simulator
        simulated_rail_id = f"order_{uuid.uuid4().hex[:14]}"
        payment_link = (
            f"https://sandbox.razorpay.com/v1/checkout/test_pay?order_id={simulated_rail_id}&amount={amount_in_paise}"
        )

        return {
            "payment_rail_id": simulated_rail_id,
            "payment_link": payment_link,
            "payment_status": "created",
            "amount_in_subunit": amount_in_paise,
            "currency": currency,
            "raw_response": {
                "id": simulated_rail_id,
                "entity": "order",
                "amount": amount_in_paise,
                "currency": currency,
                "receipt": order_id,
                "status": "created",
                "notes": notes or {},
            },
        }


# Backward-compatible alias
RazorpayPaymentRailAdapter = PaymentService
