"""Authentication & User Domain Ports."""
from abc import ABC, abstractmethod
from typing import Optional, List
from .entities import User, SavedAddress


class IUserRepository(ABC):
    """Port for platform user persistence and address management."""

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email address."""
        pass

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Fetch user by ID."""
        pass

    @abstractmethod
    def save_user(self, user: User) -> None:
        """Upsert user."""
        pass

    @abstractmethod
    def save_address(self, address: SavedAddress) -> SavedAddress:
        """Upsert a saved address."""
        pass

    @abstractmethod
    def get_user_addresses(self, user_id: str) -> List[SavedAddress]:
        """List all saved addresses for a user."""
        pass

    @abstractmethod
    def get_user_address_by_label(self, user_id: str, label: str) -> Optional[SavedAddress]:
        """Lookup a user's address by label (e.g. 'Home'). Case-insensitive."""
        pass

    @abstractmethod
    def delete_address(self, user_id: str, address_id: str) -> bool:
        """Delete a saved address for a user."""
        pass

