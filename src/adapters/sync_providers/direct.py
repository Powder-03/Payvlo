"""Direct Catalog Sync Provider."""
from typing import List, Dict, Any, Optional

from ...domain.merchant.entities import MerchantProfile
from ...domain.catalog.entities import Product
from ...domain.catalog.ports import ICatalogSyncProvider


class DirectCatalogSyncProvider(ICatalogSyncProvider):
    """Sync provider for direct in-memory or payload-based product lists."""

    def sync_catalog(
        self,
        merchant: MerchantProfile,
        raw_payload: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Product]:
        if not raw_payload:
            return []

        products: List[Product] = []
        for idx, item in enumerate(raw_payload):
            sku = item.get("sku") or f"DIR-{merchant.merchant_id.upper()[:4]}-{idx+1}"
            pid = item.get("product_id") or f"prod_{merchant.merchant_id}_{sku.lower()}"
            products.append(
                Product(
                    product_id=pid,
                    merchant_id=merchant.merchant_id,
                    sku=sku,
                    title=item.get("title", f"Product {sku}"),
                    description=item.get("description", ""),
                    price_inr=float(item.get("price_inr", item.get("price", 0.0))),
                    inventory_count=int(item.get("inventory_count", item.get("inventory", 10))),
                    category=item.get("category", merchant.category),
                    max_discount_percentage=float(
                        item.get("max_discount_percentage", merchant.max_discount_percentage)
                    ),
                    tags=item.get("tags", []),
                    metadata=item.get("metadata", {}),
                )
            )
        return products
