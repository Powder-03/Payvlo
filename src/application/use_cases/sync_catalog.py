"""Use case for refreshing and synchronizing catalog from external APIs.

Clean Architecture layer: Application.
"""
import uuid
from typing import Optional

from ...domain.merchant import CatalogSyncConfig
from ...domain.audit import AuditEntry, IAuditRepository
from ...domain.common import current_utc_timestamp
from ...domain.catalog import ICatalogRepository, ICatalogSyncProvider
from ...domain.exceptions import MerchantConfigError
from ..dto import CatalogSyncTriggerDTO, CatalogSyncResponseDTO


class SyncMerchantCatalogUseCase:
    """Use case to refresh and synchronize catalog from external store APIs."""

    def __init__(
        self,
        catalog_repo: ICatalogRepository,
        audit_repo: IAuditRepository,
        sync_provider: ICatalogSyncProvider,
    ):
        self.catalog_repo = catalog_repo
        self.audit_repo = audit_repo
        self.sync_provider = sync_provider

    def execute(
        self, merchant_id: str, trigger_req: Optional[CatalogSyncTriggerDTO] = None
    ) -> CatalogSyncResponseDTO:
        merchant = self.catalog_repo.get_merchant(merchant_id)
        if not merchant:
            raise MerchantConfigError(merchant_id, "Merchant profile not found.")

        raw_payload = trigger_req.raw_payload if trigger_req else None
        now = current_utc_timestamp()
        provider_name = merchant.sync_config.provider if merchant.sync_config else "direct"

        try:
            products = self.sync_provider.sync_catalog(merchant, raw_payload)
            synced_count = self.catalog_repo.save_products(products)

            if merchant.sync_config:
                merchant.sync_config.last_synced_at = now
                merchant.sync_config.sync_status = "SUCCESS"
                merchant.sync_config.error_message = None
            else:
                merchant.sync_config = CatalogSyncConfig(
                    provider=provider_name,
                    last_synced_at=now,
                    sync_status="SUCCESS",
                )
            self.catalog_repo.save_merchant(merchant)

            # Audit record
            self.audit_repo.record_audit(
                AuditEntry(
                    audit_id=f"aud_{uuid.uuid4().hex[:12]}",
                    timestamp=now,
                    merchant_id=merchant.merchant_id,
                    user_id_hash="catalog_sync_job",
                    action="CATALOG_SYNCED",
                    idempotency_key=None,
                    quote_id=None,
                    order_id=None,
                    amount=0.0,
                    currency=merchant.currency,
                    masked_pii_payload={"synced_count": synced_count, "provider": provider_name},
                    status="SUCCESS",
                    explainability_notes=f"Synced {synced_count} products for merchant '{merchant.merchant_id}'.",
                )
            )

            return CatalogSyncResponseDTO(
                success=True,
                merchant_id=merchant.merchant_id,
                synced_products_count=synced_count,
                provider=provider_name,
                sync_status="SUCCESS",
                last_synced_at=now,
                error_message=None,
                message=f"Successfully synced {synced_count} items from {provider_name}.",
            )
        except Exception as ex:
            if merchant.sync_config:
                merchant.sync_config.sync_status = "FAILED"
                merchant.sync_config.error_message = str(ex)
                self.catalog_repo.save_merchant(merchant)

            return CatalogSyncResponseDTO(
                success=False,
                merchant_id=merchant.merchant_id,
                synced_products_count=0,
                provider=provider_name,
                sync_status="FAILED",
                last_synced_at=now,
                error_message=str(ex),
                message=f"Catalog sync failed: {str(ex)}",
            )
