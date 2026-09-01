"""Audit Ledger Entry SQLAlchemy Model."""
from sqlalchemy import Column, String, Float, Text
from .base import Base


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
