"""Authentication & Security Controller for Platform Merchants.

Clean Architecture layer: Adapters.
Handles User Signup, Password Login, and JWT Token verification.
"""
import os
import json
import time
import hmac
import hashlib
import base64
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends, status

from ..domain.auth import User, IUserRepository
from ..domain.catalog import ICatalogRepository
from ..domain.exceptions import PolicyViolationError
from ..application.dto import (
    UserSignupInputDTO,
    UserLoginInputDTO,
    UserAuthResponseDTO,
    UserProfileDTO,
)

logger = logging.getLogger("AuthController")

# Default signing key (can be overridden via env)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "payvlo_super_secret_jwt_signing_key_2026")
TOKEN_EXPIRY_SECONDS = 86400 * 7  # 7 days


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    """Generates a standard signed HMAC-SHA256 JWT token with zero external C-dependencies."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
    }

    header_b64 = _base64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload).encode("utf-8"))
    signature_base = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = hmac.new(
        JWT_SECRET_KEY.encode("utf-8"), signature_base, hashlib.sha256
    ).digest()
    sig_b64 = _base64url_encode(signature)

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
            JWT_SECRET_KEY.encode("utf-8"), signature_base, hashlib.sha256
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


def get_current_user_dependency(user_repo: IUserRepository):
    """Factory creating FastAPI dependency for extracting authenticated user."""
    def _dependency(authorization: Optional[str] = Header(None)) -> User:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header.",
            )

        token = authorization
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()

        payload = decode_access_token(token)
        if not payload or not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or corrupted authentication token.",
            )

        user = user_repo.get_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated user account not found.",
            )
        return user

    return _dependency


def create_auth_router(
    user_repo: IUserRepository,
    catalog_repo: ICatalogRepository,
) -> APIRouter:
    """Builds FastAPI router for merchant authentication."""
    router = APIRouter(prefix="/api/v1/auth", tags=["Merchant Authentication"])
    get_user = get_current_user_dependency(user_repo)

    @router.post("/signup", response_model=UserAuthResponseDTO, status_code=status.HTTP_201_CREATED)
    def signup(request: UserSignupInputDTO):
        """Register a new merchant platform user account."""
        email_clean = request.email.strip().lower()
        if not email_clean or "@" not in email_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid email address is required.",
            )

        existing = user_repo.get_user_by_email(email_clean)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account with email '{email_clean}' already exists.",
            )

        # Generate unique user ID and secure random salt
        user_id = f"usr_{os.urandom(6).hex()}"
        salt = os.urandom(16).hex()
        password_hash = User.hash_password(request.password, salt)

        user = User(
            user_id=user_id,
            email=email_clean,
            password_hash=password_hash,
            salt=salt,
            full_name=request.full_name,
            company_name=request.company_name,
        )
        user_repo.save_user(user)

        token = create_access_token(user.user_id, user.email)
        user_profile = UserProfileDTO(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            created_at=user.created_at,
        )

        return UserAuthResponseDTO(
            success=True,
            token=token,
            token_type="bearer",
            user=user_profile,
            has_store=False,
            merchant_id=None,
            message="Account registered successfully. You can now connect your store.",
        )

    @router.post("/login", response_model=UserAuthResponseDTO)
    def login(request: UserLoginInputDTO):
        """Authenticate with email and password to receive access token."""
        email_clean = request.email.strip().lower()
        user = user_repo.get_user_by_email(email_clean)
        if not user or not user.verify_password(request.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        # Check if user has an active store connected
        merchant = catalog_repo.get_merchant_by_owner(user.user_id)
        has_store = merchant is not None
        merchant_id = merchant.merchant_id if merchant else None

        token = create_access_token(user.user_id, user.email)
        user_profile = UserProfileDTO(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            created_at=user.created_at,
        )

        return UserAuthResponseDTO(
            success=True,
            token=token,
            token_type="bearer",
            user=user_profile,
            has_store=has_store,
            merchant_id=merchant_id,
            message="Authenticated successfully.",
        )

    @router.get("/me", response_model=UserAuthResponseDTO)
    def get_my_profile(user: User = Depends(get_user)):
        """Retrieve current logged in user profile and active store status."""
        merchant = catalog_repo.get_merchant_by_owner(user.user_id)
        has_store = merchant is not None
        merchant_id = merchant.merchant_id if merchant else None

        user_profile = UserProfileDTO(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            created_at=user.created_at,
        )

        return UserAuthResponseDTO(
            success=True,
            token="",
            token_type="bearer",
            user=user_profile,
            has_store=has_store,
            merchant_id=merchant_id,
            message="Profile fetched successfully.",
        )

    return router
