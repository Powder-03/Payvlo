"""Privacy-Preserving Audit Trail DTOs.

Clean Architecture layer: Application.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AuditInspectInputDTO(BaseModel):
    merchant_id: Optional[str] = Field(default=None, description="Filter by merchant ID")
    user_id: Optional[str] = Field(default=None, description="Filter by user identity")
    limit: int = Field(default=20, ge=1, le=100)


class AuditEntryDTO(BaseModel):
    audit_id: str
    timestamp: str
    merchant_id: str
    user_id_hash: str
    action: str
    idempotency_key: Optional[str]
    quote_id: Optional[str]
    order_id: Optional[str]
    amount: float
    currency: str
    masked_pii_payload: Dict[str, Any]
    status: str
    explainability_notes: str


class AuditInspectResponseDTO(BaseModel):
    total_entries: int
    entries: List[AuditEntryDTO]
