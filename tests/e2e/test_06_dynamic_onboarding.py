"""E2E Tests 9, 10, 11: Dynamic Onboarding & Multi-Merchant Commerce."""
import uuid


def run_test(client, app):
    mcp_ctrl = app.state.mcp_controller

    print("\n[TEST 9] Testing Dynamic Shopify Merchant Onboarding & Catalog Sync...")
    shopify_onboard_payload = {
        "merchant_id": "urban_threads_shopify",
        "merchant_name": "Urban Threads D2C Apparel",
        "category": "D2C Apparel & Fashion",
        "currency": "INR",
        "max_discount_percentage": 25.0,
        "per_tx_spend_cap": 20000.0,
        "daily_merchant_spend_cap": 500000.0,
        "sync_config": {
            "provider": "shopify",
            "endpoint_url": "https://urban-threads-sample.myshopify.com",
            "access_token": "shpat_mock_test_token_123",
            "auto_sync": True,
        },
    }
    onboard_resp = client.post("/api/v1/merchants/onboard", json=shopify_onboard_payload)
    assert onboard_resp.status_code == 201, f"Shopify onboard failed: {onboard_resp.text}"
    onboard_data = onboard_resp.json()
    assert onboard_data["success"] is True
    assert onboard_data["synced_products_count"] >= 3
    print(
        f"  ✅ Onboarded '{onboard_data['merchant']['merchant_name']}' dynamically. "
        f"Synced {onboard_data['synced_products_count']} Shopify products."
    )

    agent_card_res = client.get("/.well-known/agent.json?merchant_id=urban_threads_shopify")
    assert agent_card_res.status_code == 200
    assert agent_card_res.json()["merchant_name"] == "Urban Threads D2C Apparel"
    print("  ✅ Dynamic merchant capability card verified at /.well-known/agent.json.")

    print("\n[TEST 10] Testing Custom REST API Merchant Onboarding & Ingestion...")
    custom_api_onboard_payload = {
        "merchant_id": "hyper_gear_rest",
        "merchant_name": "HyperGear Electronics",
        "category": "Consumer Electronics",
        "currency": "INR",
        "max_discount_percentage": 10.0,
        "per_tx_spend_cap": 50000.0,
        "daily_merchant_spend_cap": 1000000.0,
        "sync_config": {
            "provider": "custom_api",
            "endpoint_url": "https://api.hypergear.example/v2/catalog",
            "field_mapping": {
                "title": "item_title",
                "price": "mrp_inr",
                "sku": "product_code",
                "inventory": "stock_units",
            },
        },
    }
    custom_resp = client.post("/api/v1/merchants/onboard", json=custom_api_onboard_payload)
    assert custom_resp.status_code == 201, f"Custom API onboard failed: {custom_resp.text}"
    custom_data = custom_resp.json()
    assert custom_data["success"] is True
    assert custom_data["synced_products_count"] >= 2
    print(
        f"  ✅ Onboarded '{custom_data['merchant']['merchant_name']}' with custom field mapping. "
        f"Synced {custom_data['synced_products_count']} items."
    )

    print("\n[TEST 11] Executing Full Commerce Flow on Dynamically Onboarded Merchant...")
    new_cat_res = mcp_ctrl.search_store_catalog(query="Crewneck", merchant_id="urban_threads_shopify")
    assert new_cat_res["success"] is True
    assert len(new_cat_res["products"]) >= 1
    new_product = new_cat_res["products"][0]
    print(f"  ✅ Discovered dynamically synced product: '{new_product['title']}' (Price: ₹{new_product['price_inr']:.2f})")

    dynamic_quote_res = mcp_ctrl.request_price_quote(
        items=[{"product_id": new_product["product_id"], "quantity": 1, "requested_discount_pct": 40.0}],
        merchant_id="urban_threads_shopify",
    )
    assert dynamic_quote_res["success"] is True
    dyn_quote = dynamic_quote_res["quote"]
    assert dyn_quote["items"][0]["effective_discount_pct"] == 25.0
    print(f"  ✅ Clamped discount on dynamic merchant: 40% clamped to {dyn_quote['items'][0]['effective_discount_pct']}% (Final: ₹{dyn_quote['final_total_price']:.2f})")

    dyn_checkout_res = mcp_ctrl.execute_bounded_checkout(
        quote_id=dyn_quote["quote_id"],
        idempotency_key=f"dyn_tx_{uuid.uuid4().hex[:10]}",
        user_id="agent_claude_buyer_dynamic",
        max_spend_budget=2000.0,
        shipping_address={"line1": "Flat 801, Residency Road", "city": "Bengaluru", "phone": "9845012345"},
        merchant_id="urban_threads_shopify",
    )
    assert dyn_checkout_res["success"] is True
    dyn_order = dyn_checkout_res["order"]
    assert dyn_order["payment_status"] == "created"
    print(f"  ✅ Order placed for dynamic merchant! Order ID: {dyn_order['order_id']}, Rail: {dyn_order['payment_rail_id']}")
