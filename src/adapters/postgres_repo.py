"""SQLAlchemy PostgreSQL / SQLite Repository Adapter.

Clean Architecture layer: Adapters.
Implements ICatalogRepository and IAuditRepository ports using SQLAlchemy ORM.
Supports PostgreSQL (Neon Serverless) and local SQLite.
"""
import json
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Text,
    DateTime,
    Boolean,
    create_engine,
    desc,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from ..domain.entities import (
    MerchantProfile,
    Product,
    Address,
    QuoteItem,
    Quote,
    Order,
    AuditEntry,
    current_utc_timestamp,
)
from ..domain.exceptions import OutOfStockError
from ..domain.ports import ICatalogRepository, IAuditRepository

Base = declarative_base()


# ==========================================
# SQLAlchemy ORM Models
# ==========================================
class MerchantModel(Base):
    __tablename__ = "merchants"

    merchant_id = Column(String(64), primary_key=True)
    merchant_name = Column(String(255), nullable=False)
    category = Column(String(128), nullable=False)
    currency = Column(String(10), default="INR")
    max_discount_percentage = Column(Float, default=15.0)
    per_tx_spend_cap = Column(Float, default=10000.0)
    daily_merchant_spend_cap = Column(Float, default=100000.0)
    allowed_payment_methods_json = Column(Text, default="[]")
    support_email = Column(String(255), default="support@merchant.com")
    webhook_secret = Column(String(255), nullable=True)
    metadata_json = Column(Text, default="{}")


class ProductModel(Base):
    __tablename__ = "products"

    product_id = Column(String(64), primary_key=True)
    merchant_id = Column(String(64), nullable=False, index=True)
    sku = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    price_inr = Column(Float, nullable=False)
    inventory_count = Column(Integer, nullable=False, default=0)
    category = Column(String(128), nullable=False, index=True)
    max_discount_percentage = Column(Float, default=0.0)
    tags_json = Column(Text, default="[]")
    metadata_json = Column(Text, default="{}")


class QuoteModel(Base):
    __tablename__ = "quotes"

    quote_id = Column(String(64), primary_key=True)
    merchant_id = Column(String(64), nullable=False, index=True)
    items_json = Column(Text, nullable=False)
    total_original_price = Column(Float, nullable=False)
    total_discount_amount = Column(Float, nullable=False)
    final_total_price = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    clamped_discount_reasons_json = Column(Text, default="[]")
    created_at = Column(String(64), nullable=False)
    expires_at = Column(String(64), nullable=False)
    status = Column(String(32), default="ACTIVE")


class OrderModel(Base):
    __tablename__ = "orders"

    order_id = Column(String(64), primary_key=True)
    idempotency_key = Column(String(128), nullable=False, unique=True, index=True)
    merchant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(128), nullable=False)
    quote_id = Column(String(64), nullable=False)
    items_json = Column(Text, nullable=False)
    final_amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    shipping_address_json = Column(Text, nullable=True)
    payment_rail_id = Column(String(128), nullable=False)
    payment_status = Column(String(32), default="CREATED")
    payment_link = Column(String(512), default="")
    audit_id = Column(String(64), nullable=False)
    created_at = Column(String(64), nullable=False)
    metadata_json = Column(Text, default="{}")


class AuditEntryModel(Base):
    __tablename__ = "audit_ledger"

    audit_id = Column(String(64), primary_key=True)
    timestamp = Column(String(64), nullable=False, index=True)
    merchant_id = Column(String(64), nullable=False, index=True)
    user_id_hash = Column(String(64), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    idempotency_key = Column(String(128), nullable=True)
    quote_id = Column(String(64), nullable=True)
    order_id = Column(String(64), nullable=True)
    amount = Column(Float, default=0.0)
    currency = Column(String(10), default="INR")
    masked_pii_payload_json = Column(Text, default="{}")
    status = Column(String(32), nullable=False)
    explainability_notes = Column(Text, default="")


# ==========================================
# Repository Implementations
# ==========================================
class PostgresCatalogRepository(ICatalogRepository):
    """Catalog, quote, and order persistence using SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def _to_merchant_entity(self, m: MerchantModel) -> MerchantProfile:
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

    def save_merchant(self, merchant: MerchantProfile) -> None:
        with self.session_factory() as session:
            existing = (
                session.query(MerchantModel)
                .filter_by(merchant_id=merchant.merchant_id)
                .first()
            )
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
                    metadata_json=json.dumps(merchant.metadata),
                )
                session.add(m)
            session.commit()

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
                json.dumps(order.shipping_address.to_masked_dict())
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

        # Reconstruct Address from persisted (masked) JSON if present
        shipping_address = None
        if om.shipping_address_json:
            addr_data = json.loads(om.shipping_address_json)
            shipping_address = Address(
                line1=addr_data.get("masked_line1", "***"),
                line2=None,
                city=addr_data.get("city", ""),
                state=addr_data.get("state", ""),
                postal_code=addr_data.get("postal_code", ""),
                country=addr_data.get("country", "IN"),
                phone=addr_data.get("masked_phone"),
                email=addr_data.get("masked_email"),
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


class PostgresAuditRepository(IAuditRepository):
    """Append-only audit ledger repository using SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def record_audit(self, entry: AuditEntry) -> None:
        with self.session_factory() as session:
            a = AuditEntryModel(
                audit_id=entry.audit_id,
                timestamp=entry.timestamp,
                merchant_id=entry.merchant_id,
                user_id_hash=entry.user_id_hash,
                action=entry.action,
                idempotency_key=entry.idempotency_key,
                quote_id=entry.quote_id,
                order_id=entry.order_id,
                amount=entry.amount,
                currency=entry.currency,
                masked_pii_payload_json=json.dumps(entry.masked_pii_payload),
                status=entry.status,
                explainability_notes=entry.explainability_notes,
            )
            session.add(a)
            session.commit()

    def get_audit_trail(
        self,
        merchant_id: Optional[str] = None,
        user_id_hash: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuditEntry]:
        with self.session_factory() as session:
            q = session.query(AuditEntryModel)
            if merchant_id:
                q = q.filter(AuditEntryModel.merchant_id == merchant_id)
            if user_id_hash:
                q = q.filter(AuditEntryModel.user_id_hash == user_id_hash)
            entries = q.order_by(desc(AuditEntryModel.timestamp)).limit(limit).all()

            return [
                AuditEntry(
                    audit_id=e.audit_id,
                    timestamp=e.timestamp,
                    merchant_id=e.merchant_id,
                    user_id_hash=e.user_id_hash,
                    action=e.action,
                    idempotency_key=e.idempotency_key,
                    quote_id=e.quote_id,
                    order_id=e.order_id,
                    amount=e.amount,
                    currency=e.currency,
                    masked_pii_payload=json.loads(e.masked_pii_payload_json or "{}"),
                    status=e.status,
                    explainability_notes=e.explainability_notes,
                )
                for e in entries
            ]
