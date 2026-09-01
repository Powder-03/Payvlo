"""User Account & Saved Address SQLAlchemy Models."""
from sqlalchemy import Column, String, Boolean, Text
from .base import Base


class UserModel(Base):
    __tablename__ = "users"

    user_id = Column(String(64), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    full_name = Column(String(255), default="")
    company_name = Column(String(255), default="")
    created_at = Column(String(64), nullable=False)


class UserAddressModel(Base):
    __tablename__ = "user_addresses"

    address_id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    label = Column(String(100), nullable=False, index=True)  # "Home", "Work", etc.
    line1 = Column(String(255), nullable=False)
    line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(10), default="IN")
    phone = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True)
    delivery_notes = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(String(64), nullable=False)
