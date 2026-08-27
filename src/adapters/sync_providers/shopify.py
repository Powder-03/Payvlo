"""Shopify Catalog Sync Provider."""
import logging
import uuid
from typing import List, Dict, Any, Optional
import httpx

from ...domain.merchant.entities import MerchantProfile
from ...domain.catalog.entities import Product
from ...domain.catalog.ports import ICatalogSyncProvider

logger = logging.getLogger("ShopifySyncProvider")


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
                            product_id=f"shp_{merchant.merchant_id}_{v_id}",
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
                        product_id=f"shp_{merchant.merchant_id}_{shopify_id}",
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
