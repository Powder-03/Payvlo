"""E2E Tests 12, 13, 14: Merchant SaaS Registration, Login, Application & Sync."""


def run_test(client, app):
    print("\n[TEST 12] Verifying Merchant SaaS Registration & JWT Authentication...")
    signup_payload = {
        "email": "sarah.merchant@urbanstyle.com",
        "password": "SecurePassword123!",
        "full_name": "Sarah Jenkins",
        "company_name": "UrbanStyle D2C",
    }
    signup_resp = client.post("/api/v1/auth/signup", json=signup_payload)
    assert signup_resp.status_code == 201, f"Signup failed: {signup_resp.text}"
    signup_data = signup_resp.json()
    assert signup_data["success"] is True
    assert signup_data["token"] != ""
    assert signup_data["has_store"] is False
    auth_token = signup_data["token"]
    user_id = signup_data["user"]["user_id"]
    print(f"  ✅ Account created for '{signup_data['user']['email']}' (User ID: {user_id}). JWT token issued.")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "sarah.merchant@urbanstyle.com", "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["token"] != ""
    print("  ✅ Logged in successfully with password verification.")

    print("\n[TEST 13] Authenticated Store Application & SaaS Binding...")
    apply_payload = {
        "merchant_id": "urban_style_app",
        "merchant_name": "UrbanStyle Premium Clothing",
        "category": "Apparel & Accessories",
        "currency": "INR",
        "max_discount_percentage": 18.0,
        "per_tx_spend_cap": 30000.0,
        "daily_merchant_spend_cap": 800000.0,
        "sync_config": {
            "provider": "shopify",
            "endpoint_url": "https://urban-style-demo.myshopify.com",
            "access_token": "shpat_mock_token_456",
            "auto_sync": True,
        },
    }
    apply_resp = client.post(
        "/api/v1/merchants/apply",
        json=apply_payload,
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert apply_resp.status_code == 201, f"Store application failed: {apply_resp.text}"
    apply_data = apply_resp.json()
    assert apply_data["success"] is True
    assert apply_data["merchant"]["owner_user_id"] == user_id
    assert apply_data["synced_products_count"] >= 2
    print(
        f"  ✅ Store '{apply_data['merchant']['merchant_name']}' successfully connected to user {user_id}. "
        f"Synced {apply_data['synced_products_count']} products."
    )

    my_store_resp = client.get(
        "/api/v1/merchants/my-store",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert my_store_resp.status_code == 200
    my_store_data = my_store_resp.json()
    assert my_store_data["has_store"] is True
    assert my_store_data["merchant"]["merchant_id"] == "urban_style_app"
    assert len(my_store_data["products"]) >= 2
    print(f"  ✅ 'my-store' endpoint returned {my_store_data['total_products']} products and agent card URL.")

    print("\n[TEST 14] Testing Authenticated Re-Sync & Agent Discovery...")
    sync_my_resp = client.post(
        "/api/v1/merchants/my-store/sync",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert sync_my_resp.status_code == 200
    sync_my_data = sync_my_resp.json()
    assert sync_my_data["success"] is True
    assert sync_my_data["sync_status"] == "SUCCESS"
    print(f"  ✅ Authenticated catalog sync triggered and succeeded ({sync_my_data['synced_products_count']} items).")

    card_resp = client.get("/.well-known/agent.json?merchant_id=urban_style_app")
    assert card_resp.status_code == 200
    card_data = card_resp.json()
    assert card_data["merchant_id"] == "urban_style_app"
    assert card_data["pricing_guardrails"]["max_discount_percentage"] == 18.0
    print(f"  ✅ Universal Agent Card verified for '{card_data['name']}'.")
