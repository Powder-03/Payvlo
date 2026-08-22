"""Merchant Catalog Synchronization Providers (Shopify, Custom REST API, Direct).

Clean Architecture layer: Adapters.
Implements ICatalogSyncProvider to ingest, normalize, and transform external catalog APIs
into domain Product entities.
"""
import logging
import uuid
from typing import List, Dict, Any, Optional
import httpx

from ..domain.entities import MerchantProfile, Product
from ..domain.ports import ICatalogSyncProvider
from ..domain.exceptions import PolicyViolationError

logger = logging.getLogger("CatalogSyncProviders")


class ShopifyCatalogSyncProvider(ICatalogSyncProvider):
    """Sync provider connecting to Shopify Storefront / Admin APIs (/products.json)."""

    def sync_catalog(
        self,
        merchant: MerchantProfile,
        raw_payload: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Product]:
        """Fetches from Shopify /products.json or transforms simulated/raw payload."""
        sync_cfg = merchant.sync_config
        store_url = (sync_cfg.endpoint_url if sync_cfg else None) or ""
        store_url = store_url.rstrip("/")

        products_data: List[Dict[str, Any]] = []

        if raw_payload and len(raw_payload) > 0:
            products_data = raw_payload
        elif store_url:
            # Construct Shopify products endpoint
            if not store_url.endswith(".json"):
                api_url = f"{store_url}/products.json"
            else:
                api_url = store_url

            headers = {"User-Agent": "Universal-Agentic-Commerce-Node/1.0"}
            if sync_cfg and sync_cfg.access_token_masked:
                headers["X-Shopify-Access-Token"] = sync_cfg.access_token_masked

            try:
                with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                    resp = client.get(api_url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        products_data = data.get("products", [])
                        logger.info(f"Successfully fetched {len(products_data)} products from Shopify: {api_url}")
                    else:
                        logger.warning(
                            f"Shopify endpoint {api_url} returned {resp.status_code}. Using fallback mock items."
                        )
            except Exception as e:
                logger.warning(f"Failed to connect to live Shopify API ({e}). Generating simulated test products.")

        # If no live response was obtained, generate standard Shopify normalized simulation
        if not products_data:
            products_data = [
                {
                    "id": 8912345678,
                    "title": f"{merchant.merchant_name} Premium Cotton Crewneck",
                    "body_html": "Crafted from 100% organic combed cotton with double-needle stitching.",
                    "product_type": "Apparel",
                    "tags": "cotton, t-shirt, organic, essentials",
                    "variants": [
                        {
                            "id": 41234567890,
                            "sku": f"{merchant.merchant_id.upper()[:4]}-TSH-BLK-M",
                            "title": "Black / M",
                            "price": "1499.00",
                            "inventory_quantity": 40,
                        }
                    ],
                },
                {
                    "id": 8912345679,
                    "title": f"{merchant.merchant_name} Relaxed Fit Chinos",
                    "body_html": "Comfort-stretch cotton twill chinos designed for everyday movement.",
                    "product_type": "Apparel",
                    "tags": "chinos, pants, stretch, casual",
                    "variants": [
                        {
                            "id": 41234567891,
                            "sku": f"{merchant.merchant_id.upper()[:4]}-CHN-BEI-32",
                            "title": "Beige / 32",
                            "price": "2499.00",
                            "inventory_quantity": 25,
                        }
                    ],
                },
                {
                    "id": 8912345680,
                    "title": f"{merchant.merchant_name} Canvas Utility Backpack",
                    "body_html": "Water-resistant heavy duty canvas backpack with 15-inch padded laptop compartment.",
                    "product_type": "Accessories",
                    "tags": "bag, canvas, accessories, travel",
                    "variants": [
                        {
                            "id": 41234567892,
                            "sku": f"{merchant.merchant_id.upper()[:4]}-BAG-OLV",
                            "title": "Olive Green",
                            "price": "3299.00",
                            "inventory_quantity": 15,
                        }
                    ],
                },
            ]

        # Normalize into domain Product entities
        domain_products: List[Product] = []
        for p in products_data:
            shopify_id = str(p.get("id") or uuid.uuid4().hex[:8])
            title = p.get("title") or "Untitled Shopify Item"
            desc = p.get("body_html") or p.get("description") or ""
            cat = p.get("product_type") or merchant.category
            raw_tags = p.get("tags") or []
            if isinstance(raw_tags, str):
                tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
            else:
                tags = list(raw_tags)

            variants = p.get("variants") or []
            if variants:
                for v in variants:
                    v_id = str(v.get("id") or shopify_id)
                    sku = v.get("sku") or f"{merchant.merchant_id.upper()[:4]}-{v_id[-6:]}"
                    v_title = f"{title} ({v.get('title')})" if v.get("title") and v.get("title") != "Default Title" else title
                    price = float(v.get("price") or 0.0)
                    inventory = int(v.get("inventory_quantity") or v.get("inventory_count") or 50)
                    domain_products.append(
                        Product(
                            product_id=f"shp_{v_id}",
                            merchant_id=merchant.merchant_id,
                            sku=sku,
                            title=v_title,
                            description=desc,
                            price_inr=price,
                            inventory_count=inventory,
                            category=cat,
                            max_discount_percentage=merchant.max_discount_percentage,
                            tags=tags,
                            metadata={"shopify_product_id": shopify_id, "shopify_variant_id": v_id},
                        )
                    )
            else:
                price = float(p.get("price") or p.get("price_inr") or 999.0)
                sku = p.get("sku") or f"{merchant.merchant_id.upper()[:4]}-{shopify_id[-6:]}"
                domain_products.append(
                    Product(
                        product_id=f"shp_{shopify_id}",
                        merchant_id=merchant.merchant_id,
                        sku=sku,
                        title=title,
                        description=desc,
                        price_inr=price,
                        inventory_count=int(p.get("inventory_count") or 50),
                        category=cat,
                        max_discount_percentage=merchant.max_discount_percentage,
                        tags=tags,
                        metadata={"shopify_product_id": shopify_id},
                    )
                )

        return domain_products


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
                            # Try common catalog wrapper keys
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
            # Simulated custom REST API items
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


class DirectCatalogSyncProvider(ICatalogSyncProvider):
    """Sync provider for direct in-memory or payload-based product lists."""

    def sync_catalog(
        self,
        merchant: MerchantProfile,
        raw_payload: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Product]:
        if not raw_payload:
            return []

        products: List[Product] = []
        for idx, item in enumerate(raw_payload):
            sku = item.get("sku") or f"DIR-{merchant.merchant_id.upper()[:4]}-{idx+1}"
            pid = item.get("product_id") or f"prod_{merchant.merchant_id}_{sku.lower()}"
            products.append(
                Product(
                    product_id=pid,
                    merchant_id=merchant.merchant_id,
                    sku=sku,
                    title=item.get("title", f"Product {sku}"),
                    description=item.get("description", ""),
                    price_inr=float(item.get("price_inr", item.get("price", 0.0))),
                    inventory_count=int(item.get("inventory_count", item.get("inventory", 10))),
                    category=item.get("category", merchant.category),
                    max_discount_percentage=float(
                        item.get("max_discount_percentage", merchant.max_discount_percentage)
                    ),
                    tags=item.get("tags", []),
                    metadata=item.get("metadata", {}),
                )
            )
        return products


class CatalogSyncDispatcher(ICatalogSyncProvider):
    """Routes synchronization requests to the appropriate provider based on configuration."""

    def __init__(self):
        self.shopify_provider = ShopifyCatalogSyncProvider()
        self.custom_api_provider = CustomAPICatalogSyncProvider()
        self.direct_provider = DirectCatalogSyncProvider()

    def sync_catalog(
        self,
        merchant: MerchantProfile,
        raw_payload: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Product]:
        provider_type = "direct"
        if merchant.sync_config and merchant.sync_config.provider:
            provider_type = merchant.sync_config.provider.lower()

        if provider_type == "shopify":
            return self.shopify_provider.sync_catalog(merchant, raw_payload)
        elif provider_type == "custom_api":
            return self.custom_api_provider.sync_catalog(merchant, raw_payload)
        else:
            return self.direct_provider.sync_catalog(merchant, raw_payload)
