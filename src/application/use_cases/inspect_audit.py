"""Use case for inspecting the append-only ledger with privacy filtering.

Clean Architecture layer: Application.
"""
from typing import Optional
from ...domain.audit import AuditEntry, IAuditRepository
from ..dto import AuditInspectInputDTO, AuditInspectResponseDTO, AuditEntryDTO


class InspectAuditUseCase:
    """Use case to safely inspect the append-only ledger with privacy filtering."""

    def __init__(self, audit_repo: IAuditRepository):
        self.audit_repo = audit_repo

    def execute(self, params: AuditInspectInputDTO) -> AuditInspectResponseDTO:
        user_id_hash = None
        if params.user_id:
            user_id_hash = AuditEntry.hash_user_id(params.user_id)

        entries = self.audit_repo.get_audit_trail(
            merchant_id=params.merchant_id,
            user_id_hash=user_id_hash,
            limit=params.limit,
        )

        dtos = [
            AuditEntryDTO(
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
                masked_pii_payload=e.masked_pii_payload,
                status=e.status,
                explainability_notes=e.explainability_notes,
            )
            for e in entries
        ]

        return AuditInspectResponseDTO(
            total_entries=len(dtos),
            entries=dtos,
        )
