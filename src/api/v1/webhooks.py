"""Real-Time Ecommerce Store Webhooks API Router."""
import hmac
import hashlib
import base64
import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Header, status

from ...schemas.catalog import DirectProductInputSchema

logger = logging.getLogger("WebhookAPI")
router = APIRouter(prefix="/api/v1/webhooks", tags=["Real-Time Webhooks"])


def verify_shopify_hmac(body: bytes, hmac_header: Optional[str], secret: Optional[str]) -> bool:
    """Verifies that the incoming Shopify webhook was signed by the merchant's secret."""
    if not secret:
        return True
    if not hmac_header:
        return False

    computed = base64.b64encode(
        hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    ).decode("utf-8")
    return hmac.compare_digest(computed, hmac_header)


@router.post("/shopify/{merchant_id}")
async def handle_shopify_webhook(
    merchant_id: str,
    request: Request,
    x_shopify_topic: Optional[str] = Header(None, alias="X-Shopify-Topic"),
    x_shopify_hmac_sha256: Optional[str] = Header(None, alias="X-Shopify-Hmac-Sha256"),
):
    """Processes instant product and inventory push webhooks from Shopify."""
    catalog_service = request.app.state.catalog_service
    merchant = catalog_service.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant '{merchant_id}' not found.",
        )

    body_bytes = await request.body()
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

    if topic in ["products/update", "products/create"]:
        product_id = str(payload.get("id", ""))
        title = payload.get("title", "Untitled Product")
        body_html = payload.get("body_html", "") or ""
        product_type = payload.get("product_type", "Apparel")
        tags = (
            [t.strip() for t in payload.get("tags", "").split(",") if t.strip()]
            if isinstance(payload.get("tags"), str)
            else []
        )

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
        saved_count = 0
        if variants:
            for v in variants:
                var_id = str(v.get("id", product_id))
                sku = v.get("sku") or f"SHOPIFY-{var_id}"
                price = float(v.get("price", 0.0))
                inv = int(v.get("inventory_quantity", 10))
                var_title = (
                    f"{title} - {v.get('title')}"
                    if v.get("title") and v.get("title") != "Default Title"
                    else title
                )

                p_in = DirectProductInputSchema(
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
                catalog_service.save_product(p_in, merchant_id)
                saved_count += 1
        else:
            p_in = DirectProductInputSchema(
                sku=f"SHOPIFY-{product_id}",
                title=title,
                description=body_html[:300],
                price_inr=float(payload.get("price", 0.0)),
                inventory_count=10,
                category=product_type or merchant.category,
                max_discount_percentage=max_disc,
                tags=tags,
            )
            catalog_service.save_product(p_in, merchant_id)
            saved_count += 1

        return {
            "success": True,
            "status": "processed",
            "topic": topic,
            "updated_products_count": saved_count,
        }

    elif topic == "products/delete":
        product_id = str(payload.get("id", ""))
        existing = catalog_service.get_product(merchant_id, product_id)
        if existing:
            catalog_service.update_inventory(merchant_id, product_id, -existing.inventory_count)

        return {
            "success": True,
            "status": "deleted",
            "topic": topic,
            "product_id": product_id,
        }

    return {
        "success": True,
        "status": "ignored",
        "topic": topic,
        "message": "Topic recognized but requires no state mutation.",
    }
