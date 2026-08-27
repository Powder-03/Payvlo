"""Use case for onboarding a merchant with custom policies and sync configurations.

Clean Architecture layer: Application.
"""
import uuid
from typing import Optional

from ...domain.merchant import MerchantProfile, CatalogSyncConfig
from ...domain.audit import AuditEntry, IAuditRepository
from ...domain.common import current_utc_timestamp
from ...domain.catalog import ICatalogRepository, ICatalogSyncProvider
from ...domain.exceptions import PolicyViolationError
from ..dto import (
    MerchantOnboardInputDTO,
    MerchantOnboardResponseDTO,
    MerchantProfileDTO,
    CatalogSyncConfigDTO,
)


class OnboardMerchantUseCase:
    """Use case to onboard a new merchant with custom policies, spend caps, and catalog sync."""

    def __init__(
        self,
        catalog_repo: ICatalogRepository,
        audit_repo: IAuditRepository,
        sync_provider: ICatalogSyncProvider,
        base_url: str = "https://agentic-commerce-node.onrender.com",
    ):
        self.catalog_repo = catalog_repo
        self.audit_repo = audit_repo
        self.sync_provider = sync_provider
        self.base_url = base_url

    def execute(self, req: MerchantOnboardInputDTO) -> MerchantOnboardResponseDTO:
        existing = self.catalog_repo.get_merchant(req.merchant_id)
        if existing:
            raise PolicyViolationError(
                "MERCHANT_ALREADY_EXISTS",
                f"Merchant '{req.merchant_id}' is already registered on this node.",
            )

        sync_cfg = None
        if req.sync_config:
            sync_cfg = CatalogSyncConfig(
                provider=req.sync_config.provider,
                endpoint_url=req.sync_config.endpoint_url,
                access_token_masked=req.sync_config.access_token,
                field_mapping=req.sync_config.field_mapping,
                auto_sync=req.sync_config.auto_sync,
                sync_interval_hours=req.sync_config.sync_interval_hours,
                last_synced_at=None,
                sync_status="IDLE",
            )

        merchant = MerchantProfile(
            merchant_id=req.merchant_id,
            merchant_name=req.merchant_name,
            category=req.category,
            currency=req.currency.upper(),
            max_discount_percentage=req.max_discount_percentage,
            per_tx_spend_cap=req.per_tx_spend_cap,
            daily_merchant_spend_cap=req.daily_merchant_spend_cap,
            allowed_payment_methods=req.allowed_payment_methods,
            support_email=req.support_email,
            webhook_secret=req.webhook_secret,
            sync_config=sync_cfg,
            metadata=req.metadata,
        )

        self.catalog_repo.save_merchant(merchant)

        synced_count = 0
        now = current_utc_timestamp()

        # Seed initial direct products if provided
        if req.initial_products and len(req.initial_products) > 0:
            direct_items = [p.model_dump() for p in req.initial_products]
            products = self.sync_provider.sync_catalog(merchant, direct_items)
            synced_count = self.catalog_repo.save_products(products)
        elif merchant.sync_config and merchant.sync_config.provider in ["shopify", "custom_api"]:
            try:
                products = self.sync_provider.sync_catalog(merchant)
                synced_count = self.catalog_repo.save_products(products)
                merchant.sync_config.last_synced_at = now
                merchant.sync_config.sync_status = "SUCCESS"
                self.catalog_repo.save_merchant(merchant)
            except Exception as ex:
                merchant.sync_config.sync_status = "FAILED"
                merchant.sync_config.error_message = str(ex)
                self.catalog_repo.save_merchant(merchant)

        # Audit ledger logging
        audit_entry = AuditEntry(
            audit_id=f"aud_{uuid.uuid4().hex[:12]}",
            timestamp=now,
            merchant_id=merchant.merchant_id,
            user_id_hash="merchant_admin",
            action="MERCHANT_ONBOARDED",
            idempotency_key=None,
            quote_id=None,
            order_id=None,
            amount=0.0,
            currency=merchant.currency,
            masked_pii_payload={"category": merchant.category, "sync_provider": sync_cfg.provider if sync_cfg else "direct"},
            status="SUCCESS",
            explainability_notes=(
                f"Merchant '{merchant.merchant_name}' ({merchant.merchant_id}) successfully onboarded. "
                f"Initial products synced: {synced_count}."
            ),
        )
        self.audit_repo.record_audit(audit_entry)

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
            metadata=merchant.metadata,
        )

        agent_card_url = f"{self.base_url}/.well-known/agent.json?merchant_id={merchant.merchant_id}"

        return MerchantOnboardResponseDTO(
            success=True,
            merchant=merchant_dto,
            synced_products_count=synced_count,
            agent_card_url=agent_card_url,
            message=f"Merchant '{merchant.merchant_name}' successfully onboarded with {synced_count} products.",
        )
