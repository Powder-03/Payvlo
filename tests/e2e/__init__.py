"""Modularized E2E test suites package."""
from . import test_01_health_and_protocols
from . import test_02_discount_clamping
from . import test_03_spend_caps_and_checkout
from . import test_04_uap_a2a_protocol
from . import test_05_audit_ledger
from . import test_06_dynamic_onboarding
from . import test_07_merchant_saas_auth
from . import test_08_webhooks_and_scheduler
from . import test_09_user_addresses_and_api_keys

__all__ = [
    "test_01_health_and_protocols",
    "test_02_discount_clamping",
    "test_03_spend_caps_and_checkout",
    "test_04_uap_a2a_protocol",
    "test_05_audit_ledger",
    "test_06_dynamic_onboarding",
    "test_07_merchant_saas_auth",
    "test_08_webhooks_and_scheduler",
    "test_09_user_addresses_and_api_keys",
]

