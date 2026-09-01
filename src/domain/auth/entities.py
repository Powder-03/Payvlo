"""Authentication & User Domain Entities."""
from dataclasses import dataclass, field
import hashlib
from typing import Dict, Any, Optional
from ..common.timestamps import current_utc_timestamp



@dataclass
class User:
    """Platform merchant/business account holder."""
    user_id: str
    email: str
    password_hash: str
    salt: str
    full_name: str = ""
    company_name: str = ""
    created_at: str = field(default_factory=current_utc_timestamp)

    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        """Secure PBKDF2-HMAC password hashing with salt."""
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        )
        return key.hex()

    def verify_password(self, password: str) -> bool:
        """Verifies supplied password against stored hash and salt."""
        computed = self.hash_password(password, self.salt)
        return hashlib.sha256(computed.encode()).hexdigest() == hashlib.sha256(self.password_hash.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "full_name": self.full_name,
            "company_name": self.company_name,
            "created_at": self.created_at,
        }


@dataclass
class SavedAddress:
    """Represents a user's saved physical location or shortcut."""
    address_id: str
    user_id: str
    label: str  # e.g., "Home", "Work", "Hostel"
    line1: str
    line2: Optional[str] = None
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "IN"
    phone: Optional[str] = None
    email: Optional[str] = None
    delivery_notes: Optional[str] = None
    is_default: bool = False
    created_at: str = field(default_factory=current_utc_timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address_id": self.address_id,
            "user_id": self.user_id,
            "label": self.label,
            "line1": self.line1,
            "line2": self.line2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "phone": self.phone,
            "email": self.email,
            "delivery_notes": self.delivery_notes,
            "is_default": self.is_default,
            "created_at": self.created_at,
        }

