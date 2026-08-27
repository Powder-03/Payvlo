"""User Account SQLAlchemy ORM Model."""
from sqlalchemy import Column, String
from ..base import Base


class UserModel(Base):
    __tablename__ = "users"

    user_id = Column(String(64), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    full_name = Column(String(255), default="")
    company_name = Column(String(255), default="")
    created_at = Column(String(64), nullable=False)
