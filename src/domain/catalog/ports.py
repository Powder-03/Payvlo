"""Catalog Domain Ports."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .entities import Product
from ..merchant.entities import MerchantProfile
from ..checkout.entities import Quote, Order


class ICatalogRepository(ABC):
    """Port for catalog, inventory, merchant profiles, and order persistence."""

    @abstractmethod
    def get_merchant(self, merchant_id: str) -> Optional[MerchantProfile]:
        """Fetch merchant profile and spending rules."""
        pass

    @abstractmethod
    def get_merchant_by_owner(self, owner_user_id: str) -> Optional[MerchantProfile]:
        """Fetch merchant profile associated with an account owner."""
        pass

    @abstractmethod
    def save_merchant(self, merchant: MerchantProfile) -> None:
        """Upsert merchant profile."""
        pass

    @abstractmethod
    def list_merchants(self) -> List[MerchantProfile]:
        """Fetch all registered merchants."""
        pass

    @abstractmethod
    def save_products(self, products: List[Product]) -> int:
        """Bulk upsert products into merchant catalog. Returns count of upserted items."""
        pass

    @abstractmethod
    def get_product(self, merchant_id: str, product_id: str) -> Optional[Product]:
        """Retrieve single product by ID."""
        pass

    @abstractmethod
    def search_products(
        self,
        merchant_id: Optional[str] = None,
        query: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Product]:
        """Search and filter products across merchant catalog."""
        pass

    @abstractmethod
    def update_inventory(
        self, merchant_id: str, product_id: str, quantity_delta: int
    ) -> Product:
        """Atomically deduct or restore inventory for a product."""
        pass

    @abstractmethod
    def save_quote(self, quote: Quote) -> None:
        """Persist generated price quote."""
        pass

    @abstractmethod
    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Retrieve price quote by ID."""
        pass

    @abstractmethod
    def save_order(self, order: Order) -> None:
        """Persist settled order."""
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """Retrieve order by order ID."""
        pass

    @abstractmethod
    def get_order_by_idempotency(self, idempotency_key: str) -> Optional[Order]:
        """Retrieve previously processed order by idempotency key."""
        pass


class ICatalogSyncProvider(ABC):
    """Port for external merchant catalog synchronization engines (Shopify, Custom REST, Direct)."""

    @abstractmethod
    def sync_catalog(
        self,
        merchant: MerchantProfile,
        raw_payload: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Product]:
        """Fetch and normalize merchant catalog into standard Product domain entities."""
        pass
