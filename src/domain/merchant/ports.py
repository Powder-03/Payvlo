"""Merchant Domain Ports."""
from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import MerchantProfile


class IMerchantRepository(ABC):
    """Port for merchant profile and configuration persistence."""

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
