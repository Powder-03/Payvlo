"""E2E Tests 15, 16: Event-Driven Webhook & Background Scheduler."""
import asyncio
from src.core.scheduler import CatalogSyncScheduler


def run_test(client, app):
    mcp_ctrl = app.state.mcp_controller

    print("\n[TEST 15] Testing Instant Event-Driven Shopify Webhook Ingestion...")
    webhook_product_payload = {
        "id": 99881122,
        "title": "Urban Style Limited Edition Bomber Jacket",
        "body_html": "<p>Ultra-warm insulated tech bomber jacket.</p>",
        "product_type": "Apparel & Jackets",
        "tags": "outerwear, winter, max_discount:15",
        "variants": [
            {
                "id": 9988112201,
                "sku": "URBAN-BOMBER-BLK-M",
                "title": "Black / M",
                "price": "4999.00",
                "inventory_quantity": 25,
            }
        ],
    }
    wh_resp = client.post(
        "/api/v1/webhooks/shopify/urban_style_app",
        json=webhook_product_payload,
        headers={
            "X-Shopify-Topic": "products/update",
            "X-Shopify-Hmac-Sha256": "test_mock_hmac",
        },
    )
    assert wh_resp.status_code == 200, f"Webhook failed: {wh_resp.text}"
    wh_data = wh_resp.json()
    assert wh_data["success"] is True
    assert wh_data["status"] == "processed"
    assert wh_data["updated_products_count"] == 1

    wh_search = mcp_ctrl.search_store_catalog(query="Bomber", merchant_id="urban_style_app")
    assert wh_search["success"] is True
    assert len(wh_search["products"]) >= 1
    assert wh_search["products"][0]["sku"] == "URBAN-BOMBER-BLK-M"
    assert wh_search["products"][0]["price_inr"] == 4999.00
    print(f"  ✅ Real-time webhook processed instantly! Product '{wh_search['products'][0]['title']}' (₹{wh_search['products'][0]['price_inr']}) is live.")

    print("\n[TEST 16] Verifying Background Auto-Sync Scheduler Cycle...")
    test_scheduler = CatalogSyncScheduler(
        catalog_repo=app.state.catalog_repo,
        sync_uc=app.state.sync_catalog_uc,
        check_interval_seconds=1,
    )
    asyncio.run(test_scheduler.run_sync_cycle())
    print("  ✅ Background scheduler cycle executed across all auto_sync stores without errors.")
