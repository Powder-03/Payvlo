"""Merchant Store SQLAlchemy Model."""
from sqlalchemy import Column, String, Float, Text
from .base import Base


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
    sync_config_json = Column(Text, default="{}")
    owner_user_id = Column(String(64), nullable=True, index=True)
    metadata_json = Column(Text, default="{}")
