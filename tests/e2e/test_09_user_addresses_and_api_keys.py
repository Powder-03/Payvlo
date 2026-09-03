"""E2E Test 17: Buyer User Registration, MCP API Key, Address Book & Semantic MCP Checkout."""
import uuid


def run_test(client, app):
    print("\n[TEST 17] Buyer User Registration & Long-Lived MCP API Key Generation...")
    buyer_email = f"alex.buyer_{uuid.uuid4().hex[:6]}@example.com"
    signup_resp = client.post(
        "/api/v1/auth/signup",
        json={
            "email": buyer_email,
            "password": "BuyerPassword123!",
            "full_name": "Alex Mercer",
            "company_name": "",
            "persona": "buyer",
        },
    )
    assert signup_resp.status_code == 201, f"Buyer signup failed: {signup_resp.text}"
    buyer_data = signup_resp.json()
    auth_token = buyer_data["token"]
    user_id = buyer_data["user"]["user_id"]
    print(f"  ✅ Buyer registered (User ID: {user_id}). JWT issued.")

    # 1. Generate MCP API Key & Full Configuration
    api_key_resp = client.get(
        "/api/v1/auth/api-key",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert api_key_resp.status_code == 200, f"API key fetch failed: {api_key_resp.text}"
    api_key_data = api_key_resp.json()
    assert api_key_data["api_key"] != ""
    assert "payvlo-commerce" in api_key_data["antigravity_config_snippet"]
    assert "Authorization" in api_key_data["antigravity_config_snippet"]
    assert api_key_data["api_key"] in api_key_data["antigravity_config_snippet"]
    assert "Authorization" in api_key_data["claude_desktop_config_snippet"]
    assert api_key_data["api_key"] in api_key_data["claude_desktop_config_snippet"]
    assert api_key_data["cursor_config_snippet"] is not None
    assert api_key_data["api_key"] in api_key_data["cursor_config_snippet"]
    print(f"  ✅ MCP API Key & Full Auth Config generated successfully (Expires in {api_key_data['expires_in_days']} days).")

    # 1b. Test Configuration File Download Endpoint
    dl_antigravity = client.get(
        "/api/v1/auth/mcp-config/download?client=antigravity",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert dl_antigravity.status_code == 200
    assert "mcp_config.json" in dl_antigravity.headers.get("content-disposition", "")
    assert api_key_data["api_key"] in dl_antigravity.text

    dl_claude = client.get(
        "/api/v1/auth/mcp-config/download?client=claude",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert dl_claude.status_code == 200
    assert "claude_desktop_config.json" in dl_claude.headers.get("content-disposition", "")
    assert api_key_data["api_key"] in dl_claude.text
    print("  ✅ Downloadable MCP configuration files verified for Antigravity & Claude Desktop.")

    print("\n[TEST 18] Address Book Management (Saved Shortcuts & Dynamic Locations)...")
    # 2. Add 'Home' Saved Address
    home_addr_resp = client.post(
        "/api/v1/auth/addresses",
        json={
            "label": "Home",
            "line1": "Flat 402, Palm Grove, 100ft Road",
            "line2": "Indiranagar",
            "city": "Bengaluru",
            "state": "KA",
            "postal_code": "560038",
            "country": "IN",
            "phone": "+919876543210",
            "is_default": True,
            "delivery_notes": "Ring bell twice",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert home_addr_resp.status_code == 201, f"Save address failed: {home_addr_resp.text}"
    home_addr = home_addr_resp.json()
    assert home_addr["label"] == "Home"
    print("  ✅ Saved 'Home' address created.")

    # 3. Add 'Work' Saved Address
    work_addr_resp = client.post(
        "/api/v1/auth/addresses",
        json={
            "label": "Work",
            "line1": "Tower B, 14th Floor, Tech Hub",
            "city": "Bengaluru",
            "state": "KA",
            "postal_code": "560103",
            "country": "IN",
            "phone": "+919876543210",
            "is_default": False,
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert work_addr_resp.status_code == 201
    print("  ✅ Saved 'Work' address created.")

    # 4. List Addresses
    list_addr_resp = client.get(
        "/api/v1/auth/addresses",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert list_addr_resp.status_code == 200
    addresses = list_addr_resp.json()
    assert len(addresses) == 2
    print(f"  ✅ Retrieved {len(addresses)} addresses from address book.")

    print("\n[TEST 19] Semantic Address Resolution during MCP Checkout (address_label='Home')...")
    # 5. Get a Quote for Domino's item
    quote_resp = client.post(
        "/mcp/call",
        json={
            "name": "request_price_quote",
            "arguments": {
                "merchant_id": "dominos_in",
                "items": [{"product_id": "DOM-PIZ-001", "quantity": 1}],
            },
        },
    )
    assert quote_resp.status_code == 200
    quote_data = quote_resp.json()
    assert quote_data["success"] is True
    quote_id = quote_data["quote"]["quote_id"]

    # 6. Execute Checkout passing ONLY address_label="Home"
    idempotency_key = f"tx_home_test_{uuid.uuid4().hex[:8]}"
    checkout_resp = client.post(
        "/mcp/call",
        json={
            "name": "execute_bounded_checkout",
            "arguments": {
                "quote_id": quote_id,
                "idempotency_key": idempotency_key,
                "user_id": user_id,
                "max_spend_budget": 500.0,
                "address_label": "Home",
                "merchant_id": "dominos_in",
            },
        },
    )
    assert checkout_resp.status_code == 200
    checkout_data = checkout_resp.json()
    assert checkout_data["success"] is True
    order_id = checkout_data["order"]["order_id"]
    print(f"  ✅ MCP Checkout executed using address_label='Home' -> Order {order_id} created successfully!")

    # Verify Order in DB has the resolved address
    catalog_repo = app.state.catalog_repo
    saved_order = catalog_repo.get_order(order_id)
    assert saved_order is not None
    assert saved_order.shipping_address is not None
    assert "Indiranagar" in (saved_order.shipping_address.line2 or "") or "Palm Grove" in saved_order.shipping_address.line1
    print("  ✅ Verified that full shipping address was automatically resolved from 'Home' label in database.")

    # 7. Delete an address
    del_resp = client.delete(
        f"/api/v1/auth/addresses/{work_addr_resp.json()['address_id']}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert del_resp.status_code == 200
    print("  ✅ Address deletion verified.")
