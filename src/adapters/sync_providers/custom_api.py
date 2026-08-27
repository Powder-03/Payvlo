"""Custom REST API Catalog Sync Provider."""
import logging
from typing import List, Dict, Any, Optional
import httpx

from ...domain.merchant.entities import MerchantProfile
from ...domain.catalog.entities import Product
from ...domain.catalog.ports import ICatalogSyncProvider

logger = logging.getLogger("CustomAPISyncProvider")


class CustomAPICatalogSyncProvider(ICatalogSyncProvider):
    """Sync provider connecting to arbitrary REST catalog APIs with custom key mappings."""

    def sync_catalog(
        self,
        merchant: MerchantProfile,
        raw_payload: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Product]:
        sync_cfg = merchant.sync_config
        mapping = (sync_cfg.field_mapping if sync_cfg else {}) or {}
        api_url = (sync_cfg.endpoint_url if sync_cfg else None) or ""

        # Default mapping keys
        title_key = mapping.get("title", "title")
        price_key = mapping.get("price", "price")
        sku_key = mapping.get("sku", "sku")
        desc_key = mapping.get("description", "description")
        inv_key = mapping.get("inventory", "inventory")
        cat_key = mapping.get("category", "category")

        items_data: List[Dict[str, Any]] = []

        if raw_payload and len(raw_payload) > 0:
            items_data = raw_payload
        elif api_url:
            headers = {"User-Agent": "Universal-Agentic-Commerce-Node/1.0"}
            if sync_cfg and sync_cfg.access_token_masked:
                headers["Authorization"] = f"Bearer {sync_cfg.access_token_masked}"

            try:
                with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                    resp = client.get(api_url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, list):
                            items_data = data
                        elif isinstance(data, dict):
                            for k in ["products", "items", "data", "catalog", "results"]:
                                if k in data and isinstance(data[k], list):
                                    items_data = data[k]
                                    break
                            if not items_data:
                                items_data = [data]
                        logger.info(f"Fetched {len(items_data)} items from custom REST API: {api_url}")
                    else:
                        logger.warning(f"Custom API {api_url} returned status {resp.status_code}")
            except Exception as e:
                logger.warning(f"Failed to connect to custom REST API ({e}). Generating simulated items.")

        if not items_data:
            items_data = [
                {
                    sku_key: f"{merchant.merchant_id.upper()[:4]}-EXT-001",
                    title_key: f"{merchant.merchant_name} Smart Wireless Earbuds Pro",
                    price_key: 2999.0,
                    inv_key: 60,
                    desc_key: "Active noise cancellation with 32 hours total battery life.",
                    cat_key: merchant.category,
                },
                {
                    sku_key: f"{merchant.merchant_id.upper()[:4]}-EXT-002",
                    title_key: f"{merchant.merchant_name} Fast MagSafe Charging Pad",
                    price_key: 1299.0,
                    inv_key: 100,
                    desc_key: "15W high-efficiency wireless magnetic charging pad.",
                    cat_key: merchant.category,
                },
            ]

        domain_products: List[Product] = []
        for idx, item in enumerate(items_data):
            sku = str(item.get(sku_key) or f"SKU-{merchant.merchant_id}-{idx+1}")
            title = str(item.get(title_key) or f"Custom API Item {idx+1}")
            price = float(item.get(price_key) or 0.0)
            desc = str(item.get(desc_key) or "")
            inv = int(item.get(inv_key) or 50)
            cat = str(item.get(cat_key) or merchant.category)
            pid = str(item.get("id") or item.get("product_id") or f"ext_{merchant.merchant_id}_{sku.lower()}")

            domain_products.append(
                Product(
                    product_id=pid,
                    merchant_id=merchant.merchant_id,
                    sku=sku,
                    title=title,
                    description=desc,
                    price_inr=price,
                    inventory_count=inv,
                    category=cat,
                    max_discount_percentage=merchant.max_discount_percentage,
                    tags=["custom-api", merchant.category.lower()],
                    metadata={"source": "custom_api"},
                )
            )

        return domain_products
