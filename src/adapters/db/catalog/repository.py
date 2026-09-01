"""Catalog, Merchant, Quote & Order Repository SQLAlchemy Adapter."""
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import sessionmaker

from ....domain.catalog.entities import Product
from ....domain.catalog.ports import ICatalogRepository
from ....domain.merchant.entities import MerchantProfile, CatalogSyncConfig
from ....domain.checkout.entities import Address, QuoteItem, Quote, Order
from ....domain.exceptions import OutOfStockError
from ..merchant.models import MerchantModel
from ..checkout.models import QuoteModel, OrderModel
from .models import ProductModel


class PostgresCatalogRepository(ICatalogRepository):
    """Catalog, quote, and order persistence using SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def _to_merchant_entity(self, m: MerchantModel) -> MerchantProfile:
        sync_cfg = None
        if m.sync_config_json and m.sync_config_json != "{}":
            raw_sync = json.loads(m.sync_config_json)
            sync_cfg = CatalogSyncConfig(
                provider=raw_sync.get("provider", "direct"),
                endpoint_url=raw_sync.get("endpoint_url"),
                access_token_masked=raw_sync.get("access_token_masked"),
                field_mapping=raw_sync.get("field_mapping", {}),
                auto_sync=raw_sync.get("auto_sync", False),
                sync_interval_hours=raw_sync.get("sync_interval_hours", 24),
                last_synced_at=raw_sync.get("last_synced_at"),
                sync_status=raw_sync.get("sync_status", "IDLE"),
                error_message=raw_sync.get("error_message"),
                raw_config=raw_sync.get("raw_config", {}),
            )

        return MerchantProfile(
            merchant_id=m.merchant_id,
            merchant_name=m.merchant_name,
            category=m.category,
            currency=m.currency,
            max_discount_percentage=m.max_discount_percentage,
            per_tx_spend_cap=m.per_tx_spend_cap,
            daily_merchant_spend_cap=m.daily_merchant_spend_cap,
            allowed_payment_methods=json.loads(m.allowed_payment_methods_json or "[]"),
            support_email=m.support_email,
            webhook_secret=m.webhook_secret,
            sync_config=sync_cfg,
            owner_user_id=m.owner_user_id,
            metadata=json.loads(m.metadata_json or "{}"),
        )

    def _to_product_entity(self, p: ProductModel) -> Product:
        return Product(
            product_id=p.product_id,
            merchant_id=p.merchant_id,
            sku=p.sku,
            title=p.title,
            description=p.description,
            price_inr=p.price_inr,
            inventory_count=p.inventory_count,
            category=p.category,
            max_discount_percentage=p.max_discount_percentage,
            tags=json.loads(p.tags_json or "[]"),
            metadata=json.loads(p.metadata_json or "{}"),
        )

    def get_merchant(self, merchant_id: str) -> Optional[MerchantProfile]:
        with self.session_factory() as session:
            m = session.query(MerchantModel).filter_by(merchant_id=merchant_id).first()
            return self._to_merchant_entity(m) if m else None

    def get_merchant_by_owner(self, owner_user_id: str) -> Optional[MerchantProfile]:
        with self.session_factory() as session:
            m = session.query(MerchantModel).filter_by(owner_user_id=owner_user_id).first()
            return self._to_merchant_entity(m) if m else None

    def list_merchants(self) -> List[MerchantProfile]:
        with self.session_factory() as session:
            merchants = session.query(MerchantModel).all()
            return [self._to_merchant_entity(m) for m in merchants]

    def save_merchant(self, merchant: MerchantProfile) -> None:
        with self.session_factory() as session:
            existing = (
                session.query(MerchantModel)
                .filter_by(merchant_id=merchant.merchant_id)
                .first()
            )
            sync_json = json.dumps(merchant.sync_config.to_dict() if merchant.sync_config else {})
            if existing:
                existing.merchant_name = merchant.merchant_name
                existing.category = merchant.category
                existing.currency = merchant.currency
                existing.max_discount_percentage = merchant.max_discount_percentage
                existing.per_tx_spend_cap = merchant.per_tx_spend_cap
                existing.daily_merchant_spend_cap = merchant.daily_merchant_spend_cap
                existing.allowed_payment_methods_json = json.dumps(
                    merchant.allowed_payment_methods
                )
                existing.support_email = merchant.support_email
                existing.webhook_secret = merchant.webhook_secret
                existing.sync_config_json = sync_json
                existing.owner_user_id = merchant.owner_user_id
                existing.metadata_json = json.dumps(merchant.metadata)
            else:
                m = MerchantModel(
                    merchant_id=merchant.merchant_id,
                    merchant_name=merchant.merchant_name,
                    category=merchant.category,
                    currency=merchant.currency,
                    max_discount_percentage=merchant.max_discount_percentage,
                    per_tx_spend_cap=merchant.per_tx_spend_cap,
                    daily_merchant_spend_cap=merchant.daily_merchant_spend_cap,
                    allowed_payment_methods_json=json.dumps(
                        merchant.allowed_payment_methods
                    ),
                    support_email=merchant.support_email,
                    webhook_secret=merchant.webhook_secret,
                    sync_config_json=sync_json,
                    owner_user_id=merchant.owner_user_id,
                    metadata_json=json.dumps(merchant.metadata),
                )
                session.add(m)
            session.commit()

    def save_products(self, products: List[Product]) -> int:
        """Bulk upserts a list of Product entities into database."""
        if not products:
            return 0
        saved_count = 0
        with self.session_factory() as session:
            for p in products:
                existing = (
                    session.query(ProductModel)
                    .filter_by(merchant_id=p.merchant_id, product_id=p.product_id)
                    .first()
                )
                if not existing:
                    existing = (
                        session.query(ProductModel)
                        .filter_by(merchant_id=p.merchant_id, sku=p.sku)
                        .first()
                    )

                tags_str = json.dumps(p.tags)
                meta_str = json.dumps(p.metadata)
                if existing:
                    existing.title = p.title
                    existing.description = p.description
                    existing.price_inr = p.price_inr
                    existing.inventory_count = p.inventory_count
                    existing.category = p.category
                    existing.max_discount_percentage = p.max_discount_percentage
                    existing.tags_json = tags_str
                    existing.metadata_json = meta_str
                else:
                    pm = ProductModel(
                        product_id=p.product_id,
                        merchant_id=p.merchant_id,
                        sku=p.sku,
                        title=p.title,
                        description=p.description,
                        price_inr=p.price_inr,
                        inventory_count=p.inventory_count,
                        category=p.category,
                        max_discount_percentage=p.max_discount_percentage,
                        tags_json=tags_str,
                        metadata_json=meta_str,
                    )
                    session.add(pm)
                saved_count += 1
            session.commit()
        return saved_count

    def get_product(self, merchant_id: str, product_id: str) -> Optional[Product]:
        with self.session_factory() as session:
            p = (
                session.query(ProductModel)
                .filter(
                    ProductModel.merchant_id == merchant_id,
                    (ProductModel.product_id == product_id)
                    | (ProductModel.sku == product_id),
                )
                .first()
            )
            return self._to_product_entity(p) if p else None

    def search_products(
        self,
        merchant_id: Optional[str] = None,
        query: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Product]:
        with self.session_factory() as session:
            q = session.query(ProductModel)
            if merchant_id:
                q = q.filter(ProductModel.merchant_id == merchant_id)
            if category:
                q = q.filter(ProductModel.category.ilike(f"%{category}%"))
            if min_price is not None:
                q = q.filter(ProductModel.price_inr >= min_price)
            if max_price is not None:
                q = q.filter(ProductModel.price_inr <= max_price)
            if query:
                pattern = f"%{query.strip()}%"
                q = q.filter(
                    ProductModel.title.ilike(pattern)
                    | ProductModel.description.ilike(pattern)
                    | ProductModel.tags_json.ilike(pattern)
                    | ProductModel.sku.ilike(pattern)
                )
            products = q.offset(offset).limit(limit).all()
            return [self._to_product_entity(p) for p in products]

    def update_inventory(
        self, merchant_id: str, product_id: str, quantity_delta: int
    ) -> Product:
        with self.session_factory() as session:
            p = (
                session.query(ProductModel)
                .filter(
                    ProductModel.merchant_id == merchant_id,
                    (ProductModel.product_id == product_id)
                    | (ProductModel.sku == product_id),
                )
                .with_for_update()
                .first()
            )
            if not p:
                raise OutOfStockError(product_id, abs(quantity_delta), 0)

            new_inventory = p.inventory_count + quantity_delta
            if new_inventory < 0:
                raise OutOfStockError(
                    product_id, abs(quantity_delta), p.inventory_count
                )

            p.inventory_count = new_inventory
            session.commit()
            session.refresh(p)
            return self._to_product_entity(p)

    def save_quote(self, quote: Quote) -> None:
        with self.session_factory() as session:
            existing = (
                session.query(QuoteModel).filter_by(quote_id=quote.quote_id).first()
            )
            items_payload = json.dumps([item.to_dict() for item in quote.items])
            clamped_payload = json.dumps(quote.clamped_discount_reasons)
            if existing:
                existing.items_json = items_payload
                existing.status = quote.status
                existing.total_original_price = quote.total_original_price
                existing.total_discount_amount = quote.total_discount_amount
                existing.final_total_price = quote.final_total_price
                existing.clamped_discount_reasons_json = clamped_payload
            else:
                q = QuoteModel(
                    quote_id=quote.quote_id,
                    merchant_id=quote.merchant_id,
                    items_json=items_payload,
                    total_original_price=quote.total_original_price,
                    total_discount_amount=quote.total_discount_amount,
                    final_total_price=quote.final_total_price,
                    currency=quote.currency,
                    clamped_discount_reasons_json=clamped_payload,
                    created_at=quote.created_at,
                    expires_at=quote.expires_at,
                    status=quote.status,
                )
                session.add(q)
            session.commit()

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        with self.session_factory() as session:
            q = session.query(QuoteModel).filter_by(quote_id=quote_id).first()
            if not q:
                return None
            raw_items = json.loads(q.items_json or "[]")
            quote_items = [
                QuoteItem(
                    product_id=it["product_id"],
                    sku=it["sku"],
                    title=it["title"],
                    quantity=it["quantity"],
                    unit_price=it["unit_price"],
                    requested_discount_pct=it.get("requested_discount_pct", 0.0),
                    effective_discount_pct=it.get("effective_discount_pct", 0.0),
                    discount_amount=it.get("discount_amount", 0.0),
                    subtotal=it.get("subtotal", 0.0),
                    final_price=it.get("final_price", 0.0),
                    clamping_reason=it.get("clamping_reason"),
                )
                for it in raw_items
            ]
            return Quote(
                quote_id=q.quote_id,
                merchant_id=q.merchant_id,
                items=quote_items,
                total_original_price=q.total_original_price,
                total_discount_amount=q.total_discount_amount,
                final_total_price=q.final_total_price,
                currency=q.currency,
                clamped_discount_reasons=json.loads(
                    q.clamped_discount_reasons_json or "[]"
                ),
                created_at=q.created_at,
                expires_at=q.expires_at,
                status=q.status,
            )

    def save_order(self, order: Order) -> None:
        with self.session_factory() as session:
            addr_json = (
                json.dumps(order.shipping_address.to_dict())
                if order.shipping_address
                else None
            )
            om = OrderModel(
                order_id=order.order_id,
                idempotency_key=order.idempotency_key,
                merchant_id=order.merchant_id,
                user_id=order.user_id,
                quote_id=order.quote_id,
                items_json=json.dumps([it.to_dict() for it in order.items]),
                final_amount=order.final_amount,
                currency=order.currency,
                shipping_address_json=addr_json,
                payment_rail_id=order.payment_rail_id,
                payment_status=order.payment_status,
                payment_link=order.payment_link,
                audit_id=order.audit_id,
                created_at=order.created_at,
                metadata_json=json.dumps(order.metadata),
            )
            session.add(om)
            session.commit()

    def get_order(self, order_id: str) -> Optional[Order]:
        with self.session_factory() as session:
            om = session.query(OrderModel).filter_by(order_id=order_id).first()
            if not om:
                return None
            return self._to_order_entity(om)

    def get_order_by_idempotency(self, idempotency_key: str) -> Optional[Order]:
        with self.session_factory() as session:
            om = (
                session.query(OrderModel)
                .filter_by(idempotency_key=idempotency_key)
                .first()
            )
            if not om:
                return None
            return self._to_order_entity(om)

    def _to_order_entity(self, om: OrderModel) -> Order:
        raw_items = json.loads(om.items_json or "[]")
        items = [
            QuoteItem(
                product_id=it["product_id"],
                sku=it["sku"],
                title=it["title"],
                quantity=it["quantity"],
                unit_price=it["unit_price"],
                requested_discount_pct=it.get("requested_discount_pct", 0.0),
                effective_discount_pct=it.get("effective_discount_pct", 0.0),
                discount_amount=it.get("discount_amount", 0.0),
                subtotal=it.get("subtotal", 0.0),
                final_price=it.get("final_price", 0.0),
                clamping_reason=it.get("clamping_reason"),
            )
            for it in raw_items
        ]

        # Reconstruct Address from persisted JSON if present
        shipping_address = None
        if om.shipping_address_json:
            addr_data = json.loads(om.shipping_address_json)
            shipping_address = Address(
                line1=addr_data.get("line1") or addr_data.get("masked_line1", "***"),
                line2=addr_data.get("line2"),
                city=addr_data.get("city", ""),
                state=addr_data.get("state", ""),
                postal_code=addr_data.get("postal_code", ""),
                country=addr_data.get("country", "IN"),
                phone=addr_data.get("phone") or addr_data.get("masked_phone"),
                email=addr_data.get("email") or addr_data.get("masked_email"),
            )

        return Order(
            order_id=om.order_id,
            idempotency_key=om.idempotency_key,
            merchant_id=om.merchant_id,
            user_id=om.user_id,
            quote_id=om.quote_id,
            items=items,
            final_amount=om.final_amount,
            currency=om.currency,
            shipping_address=shipping_address,
            payment_rail_id=om.payment_rail_id,
            payment_status=om.payment_status,
            payment_link=om.payment_link,
            audit_id=om.audit_id,
            created_at=om.created_at,
            metadata=json.loads(om.metadata_json or "{}"),
        )

