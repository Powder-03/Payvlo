"""Use case for autonomous peer-to-peer buyer agent negotiation (NPCI UAP / A2A Protocol).

Clean Architecture layer: Application.
"""
from typing import List, Optional

from ...domain.ports import ICatalogRepository
from ...domain.exceptions import MerchantConfigError
from ..dto import (
    UAPNegotiateRequestDTO,
    UAPNegotiateResponseDTO,
    QuoteRequestInputDTO,
    QuoteRequestItemDTO,
)
from .request_quote import RequestQuoteUseCase


class NegotiateIntentUseCase:
    """Use case for autonomous peer-to-peer buyer agent negotiation (UAP / A2A Protocol)."""

    def __init__(
        self,
        catalog_repo: ICatalogRepository,
        request_quote_uc: RequestQuoteUseCase,
        default_merchant_id: str,
    ):
        self.catalog_repo = catalog_repo
        self.request_quote_uc = request_quote_uc
        self.default_merchant_id = default_merchant_id

    def execute(self, req: UAPNegotiateRequestDTO) -> UAPNegotiateResponseDTO:
        merchant_id = req.merchant_id or self.default_merchant_id
        merchant = self.catalog_repo.get_merchant(merchant_id)
        if not merchant:
            raise MerchantConfigError(merchant_id, "Merchant profile not found.")

        quote_items_req: List[QuoteRequestItemDTO] = []

        if req.items and len(req.items) > 0:
            quote_items_req = req.items
        elif req.target_skus_or_ids:
            for sku in req.target_skus_or_ids:
                quote_items_req.append(QuoteRequestItemDTO(product_id=sku, quantity=1))
        else:
            search_results = self.catalog_repo.search_products(
                merchant_id=merchant_id,
                query=req.intent_summary,
                limit=3,
            )
            if not search_results:
                return UAPNegotiateResponseDTO(
                    status="REJECTED",
                    quote=None,
                    counter_offer_notes=f"No matching products found for intent '{req.intent_summary}'.",
                    within_budget=False,
                    requires_approval=False,
                    settlement_endpoint="/uap/v1/transact",
                )
            for prod in search_results:
                quote_items_req.append(
                    QuoteRequestItemDTO(product_id=prod.product_id, quantity=1)
                )

        quote_dto = self.request_quote_uc.execute(
            QuoteRequestInputDTO(
                items=quote_items_req,
                overall_requested_discount_pct=merchant.max_discount_percentage,
                merchant_id=merchant_id,
            )
        )

        within_budget = quote_dto.final_total_price <= req.buyer_max_budget
        counter_notes = (
            f"Offered {len(quote_dto.items)} items for ₹{quote_dto.final_total_price:.2f} "
            f"(includes max allowable discount ₹{quote_dto.total_discount_amount:.2f})."
        )
        status = "OFFERED" if within_budget else "COUNTER_OFFER"

        return UAPNegotiateResponseDTO(
            status=status,
            quote=quote_dto,
            counter_offer_notes=counter_notes,
            within_budget=within_budget,
            requires_approval=not within_budget,
            settlement_endpoint="/uap/v1/transact",
        )
