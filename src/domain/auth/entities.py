"""Authentication & User Domain Entities."""
from dataclasses import dataclass, field
import hashlib
from typing import Dict, Any
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
