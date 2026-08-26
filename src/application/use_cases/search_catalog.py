"""Use case for discovering products in a merchant catalog.

Clean Architecture layer: Application.
"""
from typing import List
from ...domain.ports import ICatalogRepository
from ...domain.exceptions import MerchantConfigError
from ..dto import CatalogSearchInputDTO, CatalogSearchResultDTO, ProductDTO


class SearchCatalogUseCase:
    """Use case to discover products and evaluate inventory across merchant catalog."""

    def __init__(self, catalog_repo: ICatalogRepository, default_merchant_id: str):
        self.catalog_repo = catalog_repo
        self.default_merchant_id = default_merchant_id

    def execute(self, params: CatalogSearchInputDTO) -> CatalogSearchResultDTO:
        merchant_id = params.merchant_id or self.default_merchant_id
        merchant = self.catalog_repo.get_merchant(merchant_id)
        if not merchant:
            raise MerchantConfigError(merchant_id, "Merchant profile does not exist.")

        products = self.catalog_repo.search_products(
            merchant_id=merchant_id,
            query=params.query,
            category=params.category,
            min_price=params.min_price,
            max_price=params.max_price,
            limit=params.limit,
            offset=params.offset,
        )

        dtos = [
            ProductDTO(
                product_id=p.product_id,
                merchant_id=p.merchant_id,
                sku=p.sku,
                title=p.title,
                description=p.description,
                price_inr=p.price_inr,
                inventory_count=p.inventory_count,
                category=p.category,
                max_discount_percentage=p.max_discount_percentage,
                tags=p.tags,
                metadata=p.metadata,
            )
            for p in products
        ]

        return CatalogSearchResultDTO(
            merchant_id=merchant_id,
            total_count=len(dtos),
            products=dtos,
        )
