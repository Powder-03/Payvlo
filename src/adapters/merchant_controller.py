import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status

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
    MyStoreResponseDTO,
    ProductDTO,
)
from ..domain.auth import User, IUserRepository
from ..domain.catalog import ICatalogRepository
from ..domain.exceptions import DomainError
from .auth_controller import get_current_user_dependency

logger = logging.getLogger("MerchantController")


def create_merchant_router(
    onboard_uc: OnboardMerchantUseCase,
    sync_uc: SyncMerchantCatalogUseCase,
    list_uc: ListMerchantsUseCase,
    catalog_repo: ICatalogRepository,
    user_repo: Optional[IUserRepository] = None,
    base_url: str = "https://agentic-commerce-node.onrender.com",
) -> APIRouter:
    """Builds FastAPI router for merchant onboarding, dynamic catalog sync, and authenticated portal."""
    router = APIRouter(prefix="/api/v1/merchants", tags=["Merchant Onboarding & Portal"])
    get_user = get_current_user_dependency(user_repo) if user_repo else None

    # ==========================================
    # Authenticated Merchant Portal Endpoints
    # ==========================================
    if get_user:
        @router.post("/apply", response_model=MerchantOnboardResponseDTO, status_code=status.HTTP_201_CREATED)
        def apply_merchant_store(
            request: MerchantOnboardInputDTO,
            current_user: User = Depends(get_user),
        ):
            """Authenticated business owner applies / connects their store to Payvlo."""
            # Check if user already owns a store
            existing_store = catalog_repo.get_merchant_by_owner(current_user.user_id)
            if existing_store:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"You have already connected a store ('{existing_store.merchant_name}').",
                )

            try:
                # Execute onboarding and bind user_id
                res = onboard_uc.execute(request)
                # Update owner on merchant profile
                merchant = catalog_repo.get_merchant(request.merchant_id)
                if merchant:
                    merchant.owner_user_id = current_user.user_id
                    catalog_repo.save_merchant(merchant)
                    res.merchant.owner_user_id = current_user.user_id
                return res
            except DomainError as de:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=de.to_dict())
            except Exception as ex:
                logger.error(f"Failed to apply store for user {current_user.user_id}: {ex}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Store application failed: {str(ex)}",
                )

        @router.get("/my-store", response_model=MyStoreResponseDTO)
        def get_my_store(current_user: User = Depends(get_user)):
            """Retrieve the logged-in merchant's connected store and product catalog."""
            merchant = catalog_repo.get_merchant_by_owner(current_user.user_id)
            if not merchant:
                return MyStoreResponseDTO(has_store=False)

            # Fetch merchant products
            products = catalog_repo.search_products(merchant_id=merchant.merchant_id, limit=100)
            product_dtos = [ProductDTO.model_validate(p.to_dict()) for p in products]

            sync_dto = None
            if merchant.sync_config:
                sync_dto = CatalogSyncConfigDTO(
                    provider=merchant.sync_config.provider,
                    endpoint_url=merchant.sync_config.endpoint_url,
                    access_token=None,
                    field_mapping=merchant.sync_config.field_mapping,
                    auto_sync=merchant.sync_config.auto_sync,
                    sync_interval_hours=merchant.sync_config.sync_interval_hours,
                    last_synced_at=merchant.sync_config.last_synced_at,
                    sync_status=merchant.sync_config.sync_status,
                    error_message=merchant.sync_config.error_message,
                )

            merchant_dto = MerchantProfileDTO(
                merchant_id=merchant.merchant_id,
                merchant_name=merchant.merchant_name,
                category=merchant.category,
                currency=merchant.currency,
                max_discount_percentage=merchant.max_discount_percentage,
                per_tx_spend_cap=merchant.per_tx_spend_cap,
                daily_merchant_spend_cap=merchant.daily_merchant_spend_cap,
                allowed_payment_methods=merchant.allowed_payment_methods,
                support_email=merchant.support_email,
                sync_config=sync_dto,
                owner_user_id=merchant.owner_user_id,
                metadata=merchant.metadata,
            )

            agent_card_url = f"{base_url}/.well-known/agent.json?merchant_id={merchant.merchant_id}"

            return MyStoreResponseDTO(
                has_store=True,
                merchant=merchant_dto,
                total_products=len(product_dtos),
                agent_card_url=agent_card_url,
                products=product_dtos,
            )

        @router.post("/my-store/sync", response_model=CatalogSyncResponseDTO)
        def sync_my_store(
            trigger_req: Optional[CatalogSyncTriggerDTO] = None,
            current_user: User = Depends(get_user),
        ):
            """Trigger catalog synchronization for the logged-in merchant's own store."""
            merchant = catalog_repo.get_merchant_by_owner(current_user.user_id)
            if not merchant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No store connected to your account.",
                )

            try:
                return sync_uc.execute(merchant.merchant_id, trigger_req)
            except Exception as ex:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Catalog sync failed: {str(ex)}",
                )

    # ==========================================
    # Public & Direct Admin Endpoints
    # ==========================================
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
            owner_user_id=m.owner_user_id,
            metadata=m.metadata,
        )

    return router

