"""Use case for listing all onboarded merchants on the node.

Clean Architecture layer: Application.
"""
from ...domain.ports import ICatalogRepository
from ..dto import (
    MerchantListResponseDTO,
    MerchantProfileDTO,
    CatalogSyncConfigDTO,
)


class ListMerchantsUseCase:
    """Use case to list all onboarded merchants on the node."""

    def __init__(self, catalog_repo: ICatalogRepository):
        self.catalog_repo = catalog_repo

    def execute(self) -> MerchantListResponseDTO:
        merchants = self.catalog_repo.list_merchants()
        dtos = []
        for m in merchants:
            sync_dto = None
            if m.sync_config:
                sync_dto = CatalogSyncConfigDTO(
                    provider=m.sync_config.provider,
                    endpoint_url=m.sync_config.endpoint_url,
                    access_token=None,
                    field_mapping=m.sync_config.field_mapping,
                    auto_sync=m.sync_config.auto_sync,
                    sync_interval_hours=m.sync_config.sync_interval_hours,
                    last_synced_at=m.sync_config.last_synced_at,
                    sync_status=m.sync_config.sync_status,
                    error_message=m.sync_config.error_message,
                )

            dtos.append(
                MerchantProfileDTO(
                    merchant_id=m.merchant_id,
                    merchant_name=m.merchant_name,
                    category=m.category,
                    currency=m.currency,
                    max_discount_percentage=m.max_discount_percentage,
                    per_tx_spend_cap=m.per_tx_spend_cap,
                    daily_merchant_spend_cap=m.daily_merchant_spend_cap,
                    allowed_payment_methods=m.allowed_payment_methods,
                    support_email=m.support_email,
                    sync_config=sync_dto,
                    metadata=m.metadata,
                )
            )

        return MerchantListResponseDTO(total_merchants=len(dtos), merchants=dtos)
