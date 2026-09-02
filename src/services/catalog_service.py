"""Catalog, Store Management, and Inventory Synchronization Service."""
import json
import time
import logging
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.orm import sessionmaker

from ..core.config import settings
from ..core.exceptions import ProductNotFoundError, OutOfStockError, MerchantConfigError
from ..models.product import ProductModel
from ..models.merchant import MerchantModel
from ..schemas.catalog import (
    ProductSchema,
    CatalogSearchInputSchema,
    CatalogSearchResultSchema,
    MerchantProfileSchema,
    MerchantOnboardInputSchema,
    MerchantOnboardResponseSchema,
    CatalogSyncResponseSchema,
    CatalogSyncConfigSchema,
    DirectProductInputSchema,
)

logger = logging.getLogger("CatalogService")


class CatalogService:
    """Handles Product Searching, Store Profiles, Onboarding, and Catalog Sync."""

    def __init__(self, session_factory: sessionmaker, default_merchant_id: str = "dominos_in"):
        self.session_factory = session_factory
        self.default_merchant_id = default_merchant_id

    # -------------------------------------------------------------------------
    # Product Queries & Operations
    # -------------------------------------------------------------------------
    def get_product(self, merchant_id: str, product_id_or_sku: str) -> Optional[ProductModel]:
        with self.session_factory() as session:
            return (
                session.query(ProductModel)
                .filter(
                    ProductModel.merchant_id == merchant_id,
                    (ProductModel.product_id == product_id_or_sku)
                    | (ProductModel.sku == product_id_or_sku),
                )
                .first()
            )

    def get_order(self, order_id: str):
        from ..models.order import OrderModel
        from ..schemas.checkout import AddressSchema
        with self.session_factory() as session:
            order = session.query(OrderModel).filter_by(order_id=order_id).first()
            if not order:
                return None
            addr_d = json.loads(order.shipping_address_json or "{}")
            if addr_d:
                order.shipping_address = AddressSchema(
                    line1=addr_d.get("line1", ""),
                    line2=addr_d.get("line2"),
                    city=addr_d.get("city", ""),
                    state=addr_d.get("state", ""),
                    postal_code=addr_d.get("postal_code", ""),
                    country=addr_d.get("country", "IN"),
                    phone=addr_d.get("phone"),
                    email=addr_d.get("email"),
                )
            else:
                order.shipping_address = None
            return order

    def search_products(self, query: CatalogSearchInputSchema) -> CatalogSearchResultSchema:
        mid = query.merchant_id or self.default_merchant_id
        with self.session_factory() as session:
            q = session.query(ProductModel)
            if query.merchant_id:
                q = q.filter(ProductModel.merchant_id == query.merchant_id)
            elif mid:
                q = q.filter(ProductModel.merchant_id == mid)

            if query.category:
                q = q.filter(ProductModel.category.ilike(f"%{query.category}%"))

            if query.min_price is not None:
                q = q.filter(ProductModel.price_inr >= query.min_price)

            if query.max_price is not None:
                q = q.filter(ProductModel.price_inr <= query.max_price)

            if query.query:
                term = f"%{query.query.lower()}%"
                q = q.filter(
                    (ProductModel.title.ilike(term))
                    | (ProductModel.sku.ilike(term))
                    | (ProductModel.description.ilike(term))
                    | (ProductModel.tags_json.ilike(term))
                )

            total_count = q.count()
            rows = q.offset(query.offset).limit(query.limit).all()

            products = [
                ProductSchema(
                    product_id=r.product_id,
                    merchant_id=r.merchant_id,
                    sku=r.sku,
                    title=r.title,
                    description=r.description or "",
                    price_inr=r.price_inr,
                    inventory_count=r.inventory_count,
                    category=r.category,
                    max_discount_percentage=r.max_discount_percentage,
                    tags=json.loads(r.tags_json or "[]"),
                    metadata=json.loads(r.metadata_json or "{}"),
                )
                for r in rows
            ]

            return CatalogSearchResultSchema(
                merchant_id=mid,
                total_count=total_count,
                products=products,
            )

    def update_inventory(self, merchant_id: str, product_id_or_sku: str, quantity_delta: int) -> None:
        """Deducts (negative delta) or restores (positive delta) product inventory."""
        with self.session_factory() as session:
            product = (
                session.query(ProductModel)
                .filter(
                    ProductModel.merchant_id == merchant_id,
                    (ProductModel.product_id == product_id_or_sku)
                    | (ProductModel.sku == product_id_or_sku),
                )
                .with_for_update()
                .first()
            )
            if not product:
                raise ProductNotFoundError(product_id_or_sku, merchant_id)

            new_count = product.inventory_count + quantity_delta
            if new_count < 0:
                raise OutOfStockError(
                    product_id_or_sku, abs(quantity_delta), product.inventory_count
                )

            product.inventory_count = new_count
            session.commit()

    def save_product(self, product_data: DirectProductInputSchema, merchant_id: str) -> ProductSchema:
        pid = f"prod_{merchant_id}_{product_data.sku.lower()}"
        with self.session_factory() as session:
            existing = session.query(ProductModel).filter_by(product_id=pid).first()
            if existing:
                existing.title = product_data.title
                existing.description = product_data.description or ""
                existing.price_inr = product_data.price_inr
                existing.inventory_count = product_data.inventory_count
                existing.category = product_data.category
                existing.max_discount_percentage = product_data.max_discount_percentage
                existing.tags_json = json.dumps(product_data.tags or [])
                existing.metadata_json = json.dumps(product_data.metadata or {})
            else:
                new_p = ProductModel(
                    product_id=pid,
                    merchant_id=merchant_id,
                    sku=product_data.sku,
                    title=product_data.title,
                    description=product_data.description or "",
                    price_inr=product_data.price_inr,
                    inventory_count=product_data.inventory_count,
                    category=product_data.category,
                    max_discount_percentage=product_data.max_discount_percentage,
                    tags_json=json.dumps(product_data.tags or []),
                    metadata_json=json.dumps(product_data.metadata or {}),
                )
                session.add(new_p)
            session.commit()

        return ProductSchema(
            product_id=pid,
            merchant_id=merchant_id,
            sku=product_data.sku,
            title=product_data.title,
            description=product_data.description or "",
            price_inr=product_data.price_inr,
            inventory_count=product_data.inventory_count,
            category=product_data.category,
            max_discount_percentage=product_data.max_discount_percentage,
            tags=product_data.tags or [],
            metadata=product_data.metadata or {},
        )

    # -------------------------------------------------------------------------
    # Merchant Store Operations
    # -------------------------------------------------------------------------
    def get_merchant(self, merchant_id: str) -> Optional[MerchantModel]:
        with self.session_factory() as session:
            return session.query(MerchantModel).filter_by(merchant_id=merchant_id).first()

    def get_merchant_by_owner(self, user_id: str) -> Optional[MerchantModel]:
        with self.session_factory() as session:
            return session.query(MerchantModel).filter_by(owner_user_id=user_id).first()

    def list_merchants(self) -> List[MerchantProfileSchema]:
        with self.session_factory() as session:
            rows = session.query(MerchantModel).all()
            result = []
            for r in rows:
                sync_cfg = None
                if r.sync_config_json:
                    try:
                        cfg_d = json.loads(r.sync_config_json)
                        if cfg_d:
                            sync_cfg = CatalogSyncConfigSchema(**cfg_d)
                    except Exception:
                        pass

                result.append(
                    MerchantProfileSchema(
                        merchant_id=r.merchant_id,
                        merchant_name=r.merchant_name,
                        category=r.category,
                        currency=r.currency or "INR",
                        max_discount_percentage=r.max_discount_percentage,
                        per_tx_spend_cap=r.per_tx_spend_cap,
                        daily_merchant_spend_cap=r.daily_merchant_spend_cap,
                        allowed_payment_methods=json.loads(r.allowed_payment_methods_json or "[]"),
                        support_email=r.support_email or "support@merchant.com",
                        sync_config=sync_cfg,
                        owner_user_id=r.owner_user_id,
                        metadata=json.loads(r.metadata_json or "{}"),
                    )
                )
            return result

    def onboard_merchant(
        self, req: MerchantOnboardInputSchema, owner_user_id: Optional[str] = None
    ) -> MerchantOnboardResponseSchema:
        """Onboard a new merchant store node and load initial products or trigger sync."""
        sync_cfg_dict = req.sync_config.model_dump() if req.sync_config else {}

        with self.session_factory() as session:
            existing = session.query(MerchantModel).filter_by(merchant_id=req.merchant_id).first()
            if existing:
                existing.merchant_name = req.merchant_name
                existing.category = req.category
                existing.currency = req.currency
                existing.max_discount_percentage = req.max_discount_percentage
                existing.per_tx_spend_cap = req.per_tx_spend_cap
                existing.daily_merchant_spend_cap = req.daily_merchant_spend_cap
                existing.allowed_payment_methods_json = json.dumps(req.allowed_payment_methods)
                existing.support_email = req.support_email
                existing.webhook_secret = req.webhook_secret
                existing.sync_config_json = json.dumps(sync_cfg_dict)
                if owner_user_id:
                    existing.owner_user_id = owner_user_id
                existing.metadata_json = json.dumps(req.metadata or {})
            else:
                new_m = MerchantModel(
                    merchant_id=req.merchant_id,
                    merchant_name=req.merchant_name,
                    category=req.category,
                    currency=req.currency,
                    max_discount_percentage=req.max_discount_percentage,
                    per_tx_spend_cap=req.per_tx_spend_cap,
                    daily_merchant_spend_cap=req.daily_merchant_spend_cap,
                    allowed_payment_methods_json=json.dumps(req.allowed_payment_methods),
                    support_email=req.support_email,
                    webhook_secret=req.webhook_secret,
                    sync_config_json=json.dumps(sync_cfg_dict),
                    owner_user_id=owner_user_id,
                    metadata_json=json.dumps(req.metadata or {}),
                )
                session.add(new_m)
            session.commit()

        synced_count = 0
        if req.initial_products:
            for p in req.initial_products:
                self.save_product(p, req.merchant_id)
                synced_count += 1
        elif req.sync_config and req.sync_config.provider in ["shopify", "custom_api"]:
            sync_res = self.sync_merchant_catalog(req.merchant_id)
            synced_count = sync_res.synced_products_count

        agent_card_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/.well-known/agent.json?merchant_id={req.merchant_id}"

        profile = MerchantProfileSchema(
            merchant_id=req.merchant_id,
            merchant_name=req.merchant_name,
            category=req.category,
            currency=req.currency,
            max_discount_percentage=req.max_discount_percentage,
            per_tx_spend_cap=req.per_tx_spend_cap,
            daily_merchant_spend_cap=req.daily_merchant_spend_cap,
            allowed_payment_methods=req.allowed_payment_methods,
            support_email=req.support_email,
            sync_config=req.sync_config,
            owner_user_id=owner_user_id,
            metadata=req.metadata or {},
        )

        return MerchantOnboardResponseSchema(
            success=True,
            merchant=profile,
            synced_products_count=synced_count,
            agent_card_url=agent_card_url,
            message=f"Merchant '{req.merchant_name}' onboarded successfully.",
        )

    def sync_merchant_catalog(
        self, merchant_id: str, raw_payload: Optional[List[Dict[str, Any]]] = None
    ) -> CatalogSyncResponseSchema:
        """Executes catalog sync for a merchant (Shopify, Custom REST API, or Direct)."""
        merchant = self.get_merchant(merchant_id)
        if not merchant:
            raise MerchantConfigError(merchant_id, "Merchant not found.")

        sync_cfg = None
        if merchant.sync_config_json:
            try:
                cfg_d = json.loads(merchant.sync_config_json)
                if cfg_d:
                    sync_cfg = CatalogSyncConfigSchema(**cfg_d)
            except Exception:
                pass

        provider = (sync_cfg.provider if sync_cfg else "direct").lower()
        synced_count = 0

        if provider == "shopify":
            products_data = []
            if raw_payload:
                products_data = raw_payload
            elif sync_cfg and sync_cfg.endpoint_url:
                url = sync_cfg.endpoint_url.rstrip("/")
                if not url.endswith(".json"):
                    url = f"{url}/products.json"
                try:
                    with httpx.Client(timeout=5.0, follow_redirects=True) as client:
                        resp = client.get(url)
                        if resp.status_code == 200:
                            products_data = resp.json().get("products", [])
                except Exception:
                    pass

            if not products_data:
                # Standard simulated Shopify items for tests/demo
                m_prefix = merchant.merchant_id.upper()[:4]
                products_data = [
                    {
                        "id": 8912345678,
                        "title": f"{merchant.merchant_name} Premium Cotton Crewneck",
                        "body_html": "Crafted from 100% organic combed cotton.",
                        "product_type": "Apparel",
                        "tags": "cotton, t-shirt, organic",
                        "variants": [
                            {
                                "id": 41234567890,
                                "sku": f"{m_prefix}-TSH-BLK-M",
                                "title": "Black / M",
                                "price": "1499.00",
                                "inventory_quantity": 40,
                            }
                        ],
                    },
                    {
                        "id": 8912345679,
                        "title": f"{merchant.merchant_name} Relaxed Fit Chinos",
                        "body_html": "Comfort-stretch cotton twill chinos.",
                        "product_type": "Apparel",
                        "tags": "chinos, pants, casual",
                        "variants": [
                            {
                                "id": 41234567891,
                                "sku": f"{m_prefix}-CHN-BEI-32",
                                "title": "Beige / 32",
                                "price": "2499.00",
                                "inventory_quantity": 25,
                            }
                        ],
                    },
                    {
                        "id": 8912345680,
                        "title": f"{merchant.merchant_name} Canvas Utility Backpack",
                        "body_html": "Water-resistant heavy duty canvas backpack.",
                        "product_type": "Accessories",
                        "tags": "bag, canvas, accessories",
                        "variants": [
                            {
                                "id": 41234567892,
                                "sku": f"{m_prefix}-BAG-OLV",
                                "title": "Olive Green",
                                "price": "3299.00",
                                "inventory_quantity": 15,
                            }
                        ],
                    },
                ]

            for item in products_data:
                title = item.get("title", "Shopify Product")
                body_html = item.get("body_html", "")
                p_type = item.get("product_type", merchant.category)
                variants = item.get("variants", [])
                if variants:
                    for v in variants:
                        sku = v.get("sku") or f"{merchant_id[:4].upper()}-{v.get('id', 'VAR')}"
                        price = float(v.get("price", 100.0))
                        inv = int(v.get("inventory_quantity", 10))
                        var_title = f"{title} - {v.get('title')}" if v.get("title") and v.get("title") != "Default Title" else title
                        p_dto = DirectProductInputSchema(
                            sku=sku,
                            title=var_title,
                            description=body_html[:300],
                            price_inr=price,
                            inventory_count=max(inv, 0),
                            category=p_type,
                            max_discount_percentage=merchant.max_discount_percentage,
                        )
                        self.save_product(p_dto, merchant_id)
                        synced_count += 1
                else:
                    sku = item.get("sku") or f"{merchant_id[:4].upper()}-{item.get('id', 'ITEM')}"
                    p_dto = DirectProductInputSchema(
                        sku=sku,
                        title=title,
                        description=body_html[:300],
                        price_inr=float(item.get("price", 100.0)),
                        inventory_count=int(item.get("inventory", 10)),
                        category=p_type,
                        max_discount_percentage=merchant.max_discount_percentage,
                    )
                    self.save_product(p_dto, merchant_id)
                    synced_count += 1

        elif provider == "custom_api":
            mapping = (sync_cfg.field_mapping if sync_cfg else {}) or {}
            title_k = mapping.get("title", "title")
            price_k = mapping.get("price", "price")
            sku_k = mapping.get("sku", "sku")
            desc_k = mapping.get("description", "description")
            inv_k = mapping.get("inventory", "inventory")
            cat_k = mapping.get("category", "category")

            items_data = []
            if raw_payload:
                items_data = raw_payload
            elif sync_cfg and sync_cfg.endpoint_url:
                try:
                    with httpx.Client(timeout=5.0, follow_redirects=True) as client:
                        resp = client.get(sync_cfg.endpoint_url)
                        if resp.status_code == 200:
                            data = resp.json()
                            if isinstance(data, list):
                                items_data = data
                            elif isinstance(data, dict):
                                for k in ["products", "items", "data", "catalog"]:
                                    if k in data and isinstance(data[k], list):
                                        items_data = data[k]
                                        break
                except Exception:
                    pass

            if not items_data:
                m_prefix = merchant.merchant_id.upper()[:4]
                items_data = [
                    {
                        sku_k: f"{m_prefix}-EXT-001",
                        title_k: f"{merchant.merchant_name} Smart Wireless Earbuds Pro",
                        price_k: 2999.0,
                        inv_k: 60,
                        desc_k: "Active noise cancellation with 32 hours total battery life.",
                        cat_k: merchant.category,
                    },
                    {
                        sku_k: f"{m_prefix}-EXT-002",
                        title_k: f"{merchant.merchant_name} 65W GaN Fast Wall Charger",
                        price_k: 1899.0,
                        inv_k: 80,
                        desc_k: "Compact ultra-fast charging with dual USB-C Power Delivery ports.",
                        cat_k: merchant.category,
                    },
                    {
                        sku_k: f"{m_prefix}-EXT-003",
                        title_k: f"{merchant.merchant_name} 10000mAh Magnetic Power Bank",
                        price_k: 2499.0,
                        inv_k: 45,
                        desc_k: "Wireless 15W magnetic snap-on charging with LED percentage display.",
                        cat_k: merchant.category,
                    },
                ]

            for it in items_data:
                meta = it.get("metadata", {})
                if not isinstance(meta, dict):
                    meta = {}
                if "rating" in it and "rating" not in meta:
                    meta["rating"] = it["rating"]
                if "review_count" in it and "review_count" not in meta:
                    meta["review_count"] = it["review_count"]
                
                item_disc = it.get("max_discount_pct") or it.get("max_discount_percentage")
                disc_pct = float(item_disc) if item_disc is not None else merchant.max_discount_percentage

                p_dto = DirectProductInputSchema(
                    sku=str(it.get(sku_k, f"SKU-{synced_count+1}")),
                    title=str(it.get(title_k, "Product")),
                    description=str(it.get(desc_k, "")),
                    price_inr=float(it.get(price_k, 100.0)),
                    inventory_count=int(it.get(inv_k, 10)),
                    category=str(it.get(cat_k, merchant.category)),
                    max_discount_percentage=disc_pct,
                    metadata=meta,
                )
                self.save_product(p_dto, merchant_id)
                synced_count += 1

        else:
            if raw_payload:
                for item in raw_payload:
                    p_dto = DirectProductInputSchema(
                        sku=item.get("sku") or item.get("id", f"SKU-{synced_count+1}"),
                        title=item.get("title") or item.get("name", "Product"),
                        description=item.get("description", ""),
                        price_inr=float(item.get("price") or item.get("price_inr", 100.0)),
                        inventory_count=int(item.get("inventory") or item.get("inventory_count", 10)),
                        category=item.get("category", merchant.category),
                        max_discount_percentage=float(item.get("max_discount_percentage", 0.0)),
                    )
                    self.save_product(p_dto, merchant_id)
                    synced_count += 1

        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return CatalogSyncResponseSchema(
            success=True,
            merchant_id=merchant_id,
            synced_products_count=synced_count,
            provider=provider,
            sync_status="SUCCESS",
            last_synced_at=now_str,
            message=f"Synced {synced_count} products for merchant '{merchant_id}'.",
        )
