"""Merchant Management and Catalog Synchronization Controller.

Clean Architecture layer: Adapters.
Exposes REST endpoints to onboard merchants, trigger catalog syncs, and list registered stores.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status

from ..application.use_cases import (
    OnboardMerchantUseCase,
    SyncMerchantCatalogUseCase,
    ListMerchantsUseCase,
)
from ..application.dto import (
    MerchantOnboardInputDTO,
    MerchantOnboardResponseDTO,
    CatalogSyncTriggerDTO,
    CatalogSyncResponseDTO,
    MerchantListResponseDTO,
    MerchantProfileDTO,
    CatalogSyncConfigDTO,
)
from ..domain.exceptions import DomainError
from ..domain.ports import ICatalogRepository

logger = logging.getLogger("MerchantController")


def create_merchant_router(
    onboard_uc: OnboardMerchantUseCase,
    sync_uc: SyncMerchantCatalogUseCase,
    list_uc: ListMerchantsUseCase,
    catalog_repo: ICatalogRepository,
) -> APIRouter:
    """Builds FastAPI router for merchant onboarding and dynamic catalog sync."""
    router = APIRouter(prefix="/api/v1/merchants", tags=["Merchant Onboarding & Sync"])

    @router.post("/onboard", response_model=MerchantOnboardResponseDTO, status_code=status.HTTP_201_CREATED)
    def onboard_merchant(request: MerchantOnboardInputDTO):
        """Onboard a new merchant (Shopify, Custom REST API, or Direct) onto the agentic node."""
        try:
            return onboard_uc.execute(request)
        except DomainError as de:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=de.to_dict())
        except Exception as ex:
            logger.error(f"Failed to onboard merchant {request.merchant_id}: {ex}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to onboard merchant: {str(ex)}",
            )

    @router.post("/{merchant_id}/sync", response_model=CatalogSyncResponseDTO)
    def sync_merchant_catalog(merchant_id: str, trigger_req: Optional[CatalogSyncTriggerDTO] = None):
        """Trigger on-demand catalog sync from Shopify or Custom REST API for a merchant."""
        try:
            return sync_uc.execute(merchant_id, trigger_req)
        except DomainError as de:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=de.to_dict())
        except Exception as ex:
            logger.error(f"Failed to sync catalog for {merchant_id}: {ex}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Catalog sync failed: {str(ex)}",
            )

    @router.get("", response_model=MerchantListResponseDTO)
    def list_merchants():
        """List all onboarded merchants and their catalog synchronization status."""
        try:
            return list_uc.execute()
        except Exception as ex:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list merchants: {str(ex)}",
            )

    @router.get("/{merchant_id}", response_model=MerchantProfileDTO)
    def get_merchant_details(merchant_id: str):
        """Retrieve profile and spending guardrails for a specific merchant."""
        m = catalog_repo.get_merchant(merchant_id)
        if not m:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Merchant '{merchant_id}' not found.",
            )

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

        return MerchantProfileDTO(
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

    return router
