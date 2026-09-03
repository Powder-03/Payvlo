"""Authentication & User Accounts Service."""
import os
import json
import time
import hmac
import hashlib
import base64
import logging
from typing import Optional, List, Any
from sqlalchemy.orm import sessionmaker, Session
from fastapi import HTTPException, Header, status

from ..core.config import settings
from ..models.user import UserModel, UserAddressModel
from ..schemas.auth import (
    UserSignupInputSchema,
    UserLoginInputSchema,
    UserAuthResponseSchema,
    UserProfileSchema,
    SavedAddressInputSchema,
    SavedAddressResponseSchema,
    UserApiKeyResponseSchema,
)

logger = logging.getLogger("AuthService")
TOKEN_EXPIRY_SECONDS = 86400 * 7  # 7 days


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_access_token(user_id: str, email: str, role: str = "user", exp_seconds: int = TOKEN_EXPIRY_SECONDS) -> str:
    """Generates an HMAC-SHA256 JWT token with zero external C-dependencies."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_seconds,
    }
    header_b64 = _base64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload).encode("utf-8"))
    signature_base = f"{header_b64}.{payload_b64}".encode("utf-8")

    sig = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"), signature_base, hashlib.sha256
    ).digest()
    sig_b64 = _base64url_encode(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[dict]:
    """Verifies and decodes the JWT token payload."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts
        signature_base = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(
            settings.JWT_SECRET_KEY.encode("utf-8"), signature_base, hashlib.sha256
        ).digest()

        actual_sig = _base64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        if payload.get("exp") and time.time() > payload["exp"]:
            return None

        return payload
    except Exception as e:
        logger.debug(f"JWT verification failed: {e}")
        return None


def hash_password(password: str, salt: str) -> str:
    """Derives a secure password hash using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    ).hex()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    expected_hash = hash_password(password, salt)
    return hmac.compare_digest(expected_hash, password_hash)


class AuthService:
    """Handles User Signup, Password Login, Address Book, and API Key Generation."""

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        with self.session_factory() as session:
            return session.query(UserModel).filter_by(user_id=user_id).first()

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        with self.session_factory() as session:
            return (
                session.query(UserModel)
                .filter_by(email=email.strip().lower())
                .first()
            )

    def signup(self, req: UserSignupInputSchema) -> UserAuthResponseSchema:
        email_clean = req.email.strip().lower()
        if not email_clean or "@" not in email_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid email address is required.",
            )

        with self.session_factory() as session:
            existing = (
                session.query(UserModel).filter_by(email=email_clean).first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"An account with email '{email_clean}' already exists.",
                )

            user_id = f"usr_{os.urandom(6).hex()}"
            salt = os.urandom(16).hex()
            pwd_hash = hash_password(req.password, salt)
            now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            user = UserModel(
                user_id=user_id,
                email=email_clean,
                password_hash=pwd_hash,
                salt=salt,
                full_name=req.full_name,
                company_name=req.company_name or "",
                created_at=now_str,
            )
            session.add(user)
            session.commit()

        token = create_access_token(user_id, email_clean)
        profile = UserProfileSchema(
            user_id=user_id,
            email=email_clean,
            full_name=req.full_name,
            company_name=req.company_name or "",
            created_at=now_str,
        )
        return UserAuthResponseSchema(
            success=True,
            token=token,
            token_type="bearer",
            user=profile,
            has_store=False,
            merchant_id=None,
            message="Account registered successfully. You can now connect your store.",
        )

    def login(self, req: UserLoginInputSchema, catalog_service: Optional[Any] = None) -> UserAuthResponseSchema:
        email_clean = req.email.strip().lower()
        with self.session_factory() as session:
            user = session.query(UserModel).filter_by(email=email_clean).first()
            if not user or not verify_password(req.password, user.salt, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password.",
                )

            user_id = user.user_id
            user_email = user.email
            full_name = user.full_name
            company_name = user.company_name
            created_at = user.created_at

        has_store = False
        merchant_id = None
        if catalog_service:
            merchant = catalog_service.get_merchant_by_owner(user_id)
            if merchant:
                has_store = True
                merchant_id = merchant.merchant_id

        token = create_access_token(user_id, user_email)
        profile = UserProfileSchema(
            user_id=user_id,
            email=user_email,
            full_name=full_name,
            company_name=company_name,
            created_at=created_at,
        )
        return UserAuthResponseSchema(
            success=True,
            token=token,
            token_type="bearer",
            user=profile,
            has_store=has_store,
            merchant_id=merchant_id,
            message="Authenticated successfully.",
        )

    # Address Book
    def get_user_addresses(self, user_id: str) -> List[SavedAddressResponseSchema]:
        with self.session_factory() as session:
            rows = (
                session.query(UserAddressModel)
                .filter_by(user_id=user_id)
                .order_by(UserAddressModel.created_at.desc())
                .all()
            )
            return [
                SavedAddressResponseSchema(
                    address_id=r.address_id,
                    user_id=r.user_id,
                    label=r.label,
                    line1=r.line1,
                    line2=r.line2,
                    city=r.city,
                    state=r.state,
                    postal_code=r.postal_code,
                    country=r.country,
                    phone=r.phone or "",
                    email=r.email or "",
                    delivery_notes=r.delivery_notes,
                    is_default=r.is_default,
                    created_at=r.created_at,
                )
                for r in rows
            ]

    def get_user_address_by_label(self, user_id: str, label: str) -> Optional[UserAddressModel]:
        with self.session_factory() as session:
            return (
                session.query(UserAddressModel)
                .filter(
                    UserAddressModel.user_id == user_id,
                    UserAddressModel.label.ilike(label.strip()),
                )
                .first()
            )

    def save_address(self, user_id: str, input_dto: SavedAddressInputSchema, default_email: str = "") -> SavedAddressResponseSchema:
        address_id = f"addr_{os.urandom(6).hex()}"
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self.session_factory() as session:
            if input_dto.is_default:
                session.query(UserAddressModel).filter_by(user_id=user_id).update({"is_default": False})

            addr = UserAddressModel(
                address_id=address_id,
                user_id=user_id,
                label=input_dto.label.strip(),
                line1=input_dto.line1.strip(),
                line2=input_dto.line2.strip() if input_dto.line2 else None,
                city=input_dto.city.strip(),
                state=input_dto.state.strip(),
                postal_code=input_dto.postal_code.strip(),
                country=input_dto.country.strip(),
                phone=input_dto.phone.strip() if input_dto.phone else None,
                email=input_dto.email.strip() if input_dto.email else default_email,
                delivery_notes=input_dto.delivery_notes,
                is_default=input_dto.is_default,
                created_at=now_str,
            )
            session.add(addr)
            session.commit()

        return SavedAddressResponseSchema(
            address_id=address_id,
            user_id=user_id,
            label=input_dto.label.strip(),
            line1=input_dto.line1.strip(),
            line2=input_dto.line2.strip() if input_dto.line2 else None,
            city=input_dto.city.strip(),
            state=input_dto.state.strip(),
            postal_code=input_dto.postal_code.strip(),
            country=input_dto.country.strip(),
            phone=input_dto.phone.strip() if input_dto.phone else "",
            email=input_dto.email.strip() if input_dto.email else default_email,
            delivery_notes=input_dto.delivery_notes,
            is_default=input_dto.is_default,
            created_at=now_str,
        )

    def delete_address(self, user_id: str, address_id: str) -> bool:
        with self.session_factory() as session:
            addr = (
                session.query(UserAddressModel)
                .filter_by(user_id=user_id, address_id=address_id)
                .first()
            )
            if not addr:
                return False
            session.delete(addr)
            session.commit()
            return True

    def generate_agent_api_key(self, user_id: str, email: str, base_url: Optional[str] = None) -> UserApiKeyResponseSchema:
        """Generates a 1-year signed Agent API Key for MCP / A2A clients with full connection config."""
        api_token = create_access_token(user_id, email, role="buyer_agent", exp_seconds=86400 * 365)
        server_base = base_url or settings.PUBLIC_BASE_URL
        mcp_sse_url = f"{server_base.rstrip('/')}/sse"
        auth_headers = {"Authorization": f"Bearer {api_token}"}

        antigravity_config = {
            "mcpServers": {
                "payvlo-commerce": {
                    "serverUrl": mcp_sse_url,
                    "headers": auth_headers,
                }
            }
        }
        claude_config = {
            "mcpServers": {
                "payvlo-commerce": {
                    "url": mcp_sse_url,
                    "headers": auth_headers,
                }
            }
        }
        cursor_config = {
            "mcpServers": {
                "payvlo-commerce": {
                    "url": mcp_sse_url,
                    "headers": auth_headers,
                }
            }
        }

        antigravity_snippet = json.dumps(antigravity_config, indent=2)
        claude_snippet = json.dumps(claude_config, indent=2)
        cursor_snippet = json.dumps(cursor_config, indent=2)

        return UserApiKeyResponseSchema(
            user_id=user_id,
            email=email,
            api_key=api_token,
            token_type="Bearer",
            mcp_server_url=mcp_sse_url,
            expires_in_days=365,
            antigravity_config_snippet=antigravity_snippet,
            claude_desktop_config_snippet=claude_snippet,
            cursor_config_snippet=cursor_snippet,
            headers=auth_headers,
            full_config=antigravity_config,
        )
