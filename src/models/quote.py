"""Quote SQLAlchemy Model."""
from sqlalchemy import Column, String, Float, Text
from .base import Base


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
