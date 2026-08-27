"""Quote and Order SQLAlchemy ORM Models."""
from sqlalchemy import Column, String, Float, Text
from ..base import Base


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
