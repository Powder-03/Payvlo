"""Authentication & User Domain Ports."""
from abc import ABC, abstractmethod
from typing import Optional
from .entities import User


class IUserRepository(ABC):
    """Port for platform merchant user persistence."""

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
