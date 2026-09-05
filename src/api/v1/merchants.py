"""Merchant Store Management API Router."""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header, Request, status

from ...schemas.catalog import (
    MerchantProfileSchema,
    MerchantOnboardInputSchema,
    MerchantOnboardResponseSchema,
    CatalogSyncTriggerSchema,
    CatalogSyncResponseSchema,
    MerchantListResponseSchema,
    CatalogSearchInputSchema,
)
from ...schemas.auth import MyStoreResponseSchema
from .auth import get_current_user_id

router = APIRouter(prefix="/api/v1/merchants", tags=["Merchant Store Management"])


@router.post("/apply", response_model=MerchantOnboardResponseSchema, status_code=status.HTTP_201_CREATED)
@router.post("/onboard", response_model=MerchantOnboardResponseSchema, status_code=status.HTTP_201_CREATED)
def onboard_merchant(
    request: Request,
    body: MerchantOnboardInputSchema,
    authorization: Optional[str] = Header(None),
):
    """Onboards a merchant store node."""
    owner_user_id = None
    if authorization:
        try:
            owner_user_id = get_current_user_id(authorization)
        except Exception:
            pass

    catalog_service = request.app.state.catalog_service
    return catalog_service.onboard_merchant(body, owner_user_id=owner_user_id)


@router.post("/my-store/sync", response_model=CatalogSyncResponseSchema)
def sync_my_store(request: Request, authorization: Optional[str] = Header(None)):
    """Triggers sync for current authenticated merchant store."""
    user_id = get_current_user_id(authorization)
    catalog_service = request.app.state.catalog_service
    merchant = catalog_service.get_merchant_by_owner(user_id)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No merchant store connected to your account.",
        )
    return catalog_service.sync_merchant_catalog(merchant.merchant_id)


@router.post("/{merchant_id}/sync", response_model=CatalogSyncResponseSchema)
def sync_merchant_catalog(
    request: Request,
    merchant_id: str,
    trigger_dto: Optional[CatalogSyncTriggerSchema] = None,
):
    """Triggers catalog inventory synchronization for a merchant."""
    catalog_service = request.app.state.catalog_service
    payload = trigger_dto.raw_payload if trigger_dto else None
    return catalog_service.sync_merchant_catalog(merchant_id, raw_payload=payload)


@router.get("", response_model=MerchantListResponseSchema)
def list_merchants(request: Request):
    """Lists all active merchants registered on this node."""
    catalog_service = request.app.state.catalog_service
    merchants = catalog_service.list_merchants()
    return MerchantListResponseSchema(total_merchants=len(merchants), merchants=merchants)


@router.get("/my-store", response_model=MyStoreResponseSchema)
@router.get("/me/store", response_model=MyStoreResponseSchema)
def get_my_store(request: Request, authorization: Optional[str] = Header(None)):
    """Retrieves the store connected to the current authenticated merchant account."""
    user_id = get_current_user_id(authorization)
    catalog_service = request.app.state.catalog_service
    merchant = catalog_service.get_merchant_by_owner(user_id)
    if not merchant:
        return MyStoreResponseSchema(has_store=False)

    products_res = catalog_service.search_products(
        CatalogSearchInputSchema(merchant_id=merchant.merchant_id, limit=100)
    )

    from ...core.config import settings
    agent_card_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/.well-known/agent.json?merchant_id={merchant.merchant_id}"

    # Build schema
    sync_cfg = None
    if merchant.sync_config_json:
        try:
            import json
            from ...schemas.catalog import CatalogSyncConfigSchema
            cfg_d = json.loads(merchant.sync_config_json)
            if cfg_d:
                sync_cfg = CatalogSyncConfigSchema(**cfg_d)
        except Exception:
            pass

    import json
    merchant_profile = MerchantProfileSchema(
        merchant_id=merchant.merchant_id,
        merchant_name=merchant.merchant_name,
        category=merchant.category,
        currency=merchant.currency or "INR",
        max_discount_percentage=merchant.max_discount_percentage,
        per_tx_spend_cap=merchant.per_tx_spend_cap,
        daily_merchant_spend_cap=merchant.daily_merchant_spend_cap,
        allowed_payment_methods=json.loads(merchant.allowed_payment_methods_json or "[]"),
        support_email=merchant.support_email or "support@merchant.com",
        sync_config=sync_cfg,
        owner_user_id=merchant.owner_user_id,
        metadata=json.loads(merchant.metadata_json or "{}"),
    )

    orders = catalog_service.get_orders_by_merchant(merchant.merchant_id)

    return MyStoreResponseSchema(
        has_store=True,
        merchant=merchant_profile,
        total_products=products_res.total_count,
        agent_card_url=agent_card_url,
        products=products_res.products,
        orders=orders,
    )


@router.get("/my-store/orders")
def get_my_store_orders(request: Request, authorization: Optional[str] = Header(None)):
    """Retrieves all orders received by the current authenticated merchant store."""
    user_id = get_current_user_id(authorization)
    catalog_service = request.app.state.catalog_service
    merchant = catalog_service.get_merchant_by_owner(user_id)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No merchant store connected to your account.",
        )
    return catalog_service.get_orders_by_merchant(merchant.merchant_id)


@router.get("/{merchant_id}")
def get_merchant_details(request: Request, merchant_id: str):
    """Gets public summary of a merchant store."""
    catalog_service = request.app.state.catalog_service
    merchant = catalog_service.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant '{merchant_id}' not found.",
        )

    products_res = catalog_service.search_products(
        CatalogSearchInputSchema(merchant_id=merchant_id, limit=50)
    )
    return {
        "merchant": {
            "merchant_id": merchant.merchant_id,
            "merchant_name": merchant.merchant_name,
            "category": merchant.category,
            "currency": merchant.currency or "INR",
            "max_discount_percentage": merchant.max_discount_percentage,
            "per_tx_spend_cap": merchant.per_tx_spend_cap,
            "daily_merchant_spend_cap": merchant.daily_merchant_spend_cap,
        },
        "catalog": {
            "total_items": products_res.total_count,
            "products": products_res.products,
        },
    }
