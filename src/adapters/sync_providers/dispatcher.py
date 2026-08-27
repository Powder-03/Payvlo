"""Catalog Sync Dispatcher."""
from typing import List, Dict, Any, Optional

from ...domain.merchant.entities import MerchantProfile
from ...domain.catalog.entities import Product
from ...domain.catalog.ports import ICatalogSyncProvider
from .shopify import ShopifyCatalogSyncProvider
from .custom_api import CustomAPICatalogSyncProvider
from .direct import DirectCatalogSyncProvider


class CatalogSyncDispatcher(ICatalogSyncProvider):
    """Routes synchronization requests to the appropriate provider based on configuration."""

    def __init__(self):
        self.shopify_provider = ShopifyCatalogSyncProvider()
        self.custom_api_provider = CustomAPICatalogSyncProvider()
        self.direct_provider = DirectCatalogSyncProvider()

    def sync_catalog(
        self,
        merchant: MerchantProfile,
        raw_payload: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Product]:
        provider_type = "direct"
        if merchant.sync_config and merchant.sync_config.provider:
            provider_type = merchant.sync_config.provider.lower()

        if provider_type == "shopify":
            return self.shopify_provider.sync_catalog(merchant, raw_payload)
        elif provider_type == "custom_api":
            return self.custom_api_provider.sync_catalog(merchant, raw_payload)
        else:
            return self.direct_provider.sync_catalog(merchant, raw_payload)
