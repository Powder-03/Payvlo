"""Shopify Real-Time Webhook Controller.

Clean Architecture layer: Adapters.
Handles instant event-driven synchronization for Shopify:
- `products/create` and `products/update`
- `products/delete`
- `inventory_levels/update`
Verifies cryptographic HMAC-SHA256 signatures over raw body.
"""
import hmac
import hashlib
import base64
import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Header, status

from ..domain.entities import Product
from ..domain.ports import ICatalogRepository

logger = logging.getLogger("WebhookController")


def verify_shopify_hmac(body: bytes, hmac_header: Optional[str], secret: Optional[str]) -> bool:
    """Verifies that the incoming Shopify webhook was signed by the merchant's secret."""
    if not secret:
        # If no webhook secret is configured for merchant, accept (e.g. test mode)
        return True
    if not hmac_header:
        return False

    computed = base64.b64encode(
        hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    ).decode("utf-8")

    return hmac.compare_digest(computed, hmac_header)


def create_webhook_router(catalog_repo: ICatalogRepository) -> APIRouter:
    """Builds FastAPI router for incoming third-party ecommerce webhooks."""
    router = APIRouter(prefix="/api/v1/webhooks", tags=["Real-Time Webhooks"])

    @router.post("/shopify/{merchant_id}")
    async def handle_shopify_webhook(
        merchant_id: str,
        request: Request,
        x_shopify_topic: Optional[str] = Header(None, alias="X-Shopify-Topic"),
        x_shopify_hmac_sha256: Optional[str] = Header(None, alias="X-Shopify-Hmac-Sha256"),
    ):
        """Processes instant product and inventory push webhooks from Shopify."""
        merchant = catalog_repo.get_merchant(merchant_id)
        if not merchant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Merchant '{merchant_id}' not found.",
            )

        body_bytes = await request.body()

        # 1. Verify HMAC Signature
        if not verify_shopify_hmac(body_bytes, x_shopify_hmac_sha256, merchant.webhook_secret):
            logger.warning(f"Invalid HMAC signature for Shopify webhook on merchant {merchant_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Shopify HMAC signature.",
            )

        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception as e:
            logger.error(f"Failed to parse JSON webhook body: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload.",
            )

        topic = (x_shopify_topic or "").lower().strip()
        logger.info(f"Received Shopify webhook [{topic}] for merchant [{merchant_id}]")

        # 2. Process Topic
        if topic in ["products/update", "products/create"]:
            # Single product updated in Shopify
            product_id = str(payload.get("id", ""))
            title = payload.get("title", "Untitled Product")
            body_html = payload.get("body_html", "") or ""
            product_type = payload.get("product_type", "Apparel")
            tags = [t.strip() for t in payload.get("tags", "").split(",") if t.strip()] if isinstance(payload.get("tags"), str) else []

            # Check discount tag
            max_disc = merchant.max_discount_percentage
            for tag in tags:
                tag_l = tag.lower()
                if tag_l in ["no-discount", "no_discount"]:
                    max_disc = 0.0
                elif tag_l.startswith("max_discount:") or tag_l.startswith("discount:"):
                    try:
                        max_disc = min(float(tag_l.split(":")[-1]), merchant.max_discount_percentage)
                    except ValueError:
                        pass

            variants = payload.get("variants", [])
            products_to_save = []

            if variants:
                for v in variants:
                    var_id = str(v.get("id", product_id))
                    sku = v.get("sku") or f"SHOPIFY-{var_id}"
                    price = float(v.get("price", 0.0))
                    inv = int(v.get("inventory_quantity", 10))
                    var_title = f"{title} - {v.get('title')}" if v.get("title") and v.get("title") != "Default Title" else title

                    products_to_save.append(
                        Product(
                            product_id=var_id,
                            merchant_id=merchant_id,
                            sku=sku,
                            title=var_title,
                            description=body_html[:300],
                            price_inr=price,
                            inventory_count=max(inv, 0),
                            category=product_type or merchant.category,
                            max_discount_percentage=max_disc,
                            tags=tags,
                            metadata={"shopify_product_id": product_id, "variant_id": var_id},
                        )
                    )
            else:
                products_to_save.append(
                    Product(
                        product_id=product_id,
                        merchant_id=merchant_id,
                        sku=f"SHOPIFY-{product_id}",
                        title=title,
                        description=body_html[:300],
                        price_inr=float(payload.get("price", 0.0)),
                        inventory_count=10,
                        category=product_type or merchant.category,
                        max_discount_percentage=max_disc,
                        tags=tags,
                    )
                )

            catalog_repo.save_products(merchant_id, products_to_save)
            logger.info(f"Real-time webhook updated {len(products_to_save)} items for {merchant_id}")

            return {
                "success": True,
                "status": "processed",
                "topic": topic,
                "updated_products_count": len(products_to_save),
            }

        elif topic == "products/delete":
            # Product deleted in Shopify -> set inventory to 0 in Payvlo
            product_id = str(payload.get("id", ""))
            existing = catalog_repo.get_product(merchant_id, product_id)
            if existing:
                catalog_repo.update_inventory(merchant_id, product_id, 0)
                logger.info(f"Real-time webhook marked deleted product {product_id} as 0 inventory.")

            return {
                "success": True,
                "status": "deleted",
                "topic": topic,
                "product_id": product_id,
            }

        elif topic == "inventory_levels/update":
            # Direct inventory update
            inventory_item_id = str(payload.get("inventory_item_id", ""))
            available = int(payload.get("available", 0))
            # Scan matching product
            products = catalog_repo.search_products(merchant_id=merchant_id, limit=200)
            updated = False
            for p in products:
                if p.metadata.get("inventory_item_id") == inventory_item_id or p.product_id == inventory_item_id:
                    catalog_repo.update_inventory(merchant_id, p.product_id, max(available, 0))
                    updated = True
                    break

            return {
                "success": True,
                "status": "inventory_updated",
                "topic": topic,
                "matched": updated,
            }

        return {
            "success": True,
            "status": "ignored",
            "topic": topic,
            "message": "Topic recognized but requires no state mutation.",
        }

    return router
