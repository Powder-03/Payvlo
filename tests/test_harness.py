"""Autonomous E2E Test Suite Orchestrator.

Clean Architecture layer: Tests.
Orchestrates the modular E2E test suites in `tests/e2e/`:
- Test 1 & 2: Health, Discovery & MCP Tool Discovery
- Test 3: Deterministic Discount Clamping Guardrails
- Test 4, 5, 6: Spend Cap Rejection, Bounded Checkout & Idempotency Replay
- Test 7: Universal Agent Protocol (UAP / A2A) Flow
- Test 8: Privacy-Preserving Masked PII Audit Ledger
- Test 9, 10, 11: Dynamic Onboarding & Multi-Merchant Commerce
- Test 12, 13, 14: Merchant SaaS Registration, Login, Application & Sync
- Test 15, 16: Event-Driven Webhook & Background Scheduler
"""
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from src.main import create_application
from tests.seed_test_data import seed_test_environment
from tests.e2e import (
    test_01_health_and_protocols,
    test_02_discount_clamping,
    test_03_spend_caps_and_checkout,
    test_04_uap_a2a_protocol,
    test_05_audit_ledger,
    test_06_dynamic_onboarding,
    test_07_merchant_saas_auth,
    test_08_webhooks_and_scheduler,
    test_09_user_addresses_and_api_keys,
)


def run_e2e_suite():
    print("=" * 80)
    print("🚀 STARTING MODULAR AGENTIC COMMERCE NODE E2E TEST SUITE")
    print("=" * 80)

    seed_test_environment()
    app = create_application()
    client = TestClient(app)

    # Execute modular test suites sequentially
    test_01_health_and_protocols.run_test(client, app)
    quote = test_02_discount_clamping.run_test(client, app)
    test_03_spend_caps_and_checkout.run_test(client, app, quote)
    test_04_uap_a2a_protocol.run_test(client, app)
    test_05_audit_ledger.run_test(client, app)
    test_06_dynamic_onboarding.run_test(client, app)
    test_07_merchant_saas_auth.run_test(client, app)
    test_08_webhooks_and_scheduler.run_test(client, app)
    test_09_user_addresses_and_api_keys.run_test(client, app)

    print("\n" + "=" * 80)
    print("🎉 ALL 19 E2E INTEGRATION, SAAS AUTH, ADDRESS BOOK & MCP TOOL TESTS PASSED!")
    print("=" * 80)



def test_e2e_flow():
    """Pytest entrypoint."""
    run_e2e_suite()


if __name__ == "__main__":
    run_e2e_suite()
