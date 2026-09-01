"""Product Catalog SQLAlchemy Model."""
from sqlalchemy import Column, String, Float, Integer, Text
from .base import Base


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
