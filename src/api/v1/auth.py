"""Authentication & User Address Book API Router."""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header, Request, Response, status

from ...schemas.auth import (
    UserSignupInputSchema,
    UserLoginInputSchema,
    UserAuthResponseSchema,
    UserProfileSchema,
    SavedAddressInputSchema,
    SavedAddressResponseSchema,
    UserApiKeyResponseSchema,
)
from ...services.auth_service import decode_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["User & Merchant Authentication"])


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Dependency extracting user ID from Bearer token."""
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
    return payload["sub"]


@router.post("/signup", response_model=UserAuthResponseSchema, status_code=status.HTTP_201_CREATED)
def signup(request: Request, body: UserSignupInputSchema):
    auth_service = request.app.state.auth_service
    return auth_service.signup(body)


@router.post("/login", response_model=UserAuthResponseSchema)
def login(request: Request, body: UserLoginInputSchema):
    auth_service = request.app.state.auth_service
    catalog_service = getattr(request.app.state, "catalog_service", None)
    return auth_service.login(body, catalog_service=catalog_service)


@router.get("/me", response_model=UserAuthResponseSchema)
def get_my_profile(request: Request, authorization: Optional[str] = Header(None)):
    user_id = get_current_user_id(authorization)
    auth_service = request.app.state.auth_service
    catalog_service = getattr(request.app.state, "catalog_service", None)
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user account not found.",
        )

    has_store = False
    merchant_id = None
    if catalog_service:
        merchant = catalog_service.get_merchant_by_owner(user_id)
        if merchant:
            has_store = True
            merchant_id = merchant.merchant_id

    profile = UserProfileSchema(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        created_at=user.created_at,
    )
    return UserAuthResponseSchema(
        success=True,
        token="",
        token_type="bearer",
        user=profile,
        has_store=has_store,
        merchant_id=merchant_id,
        message="Profile fetched successfully.",
    )


# -------------------------------------------------------------------------
# Address Book
# -------------------------------------------------------------------------
@router.get("/addresses", response_model=List[SavedAddressResponseSchema])
def get_addresses(request: Request, authorization: Optional[str] = Header(None)):
    user_id = get_current_user_id(authorization)
    auth_service = request.app.state.auth_service
    return auth_service.get_user_addresses(user_id)


@router.post("/addresses", response_model=SavedAddressResponseSchema, status_code=status.HTTP_201_CREATED)
def create_address(
    request: Request,
    body: SavedAddressInputSchema,
    authorization: Optional[str] = Header(None),
):
    user_id = get_current_user_id(authorization)
    auth_service = request.app.state.auth_service
    user = auth_service.get_user_by_id(user_id)
    default_email = user.email if user else ""
    return auth_service.save_address(user_id, body, default_email=default_email)


@router.delete("/addresses/{address_id}")
def delete_address(
    request: Request,
    address_id: str,
    authorization: Optional[str] = Header(None),
):
    user_id = get_current_user_id(authorization)
    auth_service = request.app.state.auth_service
    deleted = auth_service.delete_address(user_id, address_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found.")
    return {"success": True, "message": "Address deleted successfully."}


# -------------------------------------------------------------------------
# Agent API Key
# -------------------------------------------------------------------------
@router.post("/api-key", response_model=UserApiKeyResponseSchema)
@router.get("/api-key", response_model=UserApiKeyResponseSchema)
def get_or_generate_api_key(
    request: Request,
    authorization: Optional[str] = Header(None),
    base_url: Optional[str] = None,
):
    user_id = get_current_user_id(authorization)
    auth_service = request.app.state.auth_service
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user account not found.",
        )
    return auth_service.generate_agent_api_key(user.user_id, user.email, base_url=base_url)


@router.get("/mcp-config/download")
def download_mcp_config(
    request: Request,
    client: str = "antigravity",
    authorization: Optional[str] = Header(None),
    token: Optional[str] = None,
    base_url: Optional[str] = None,
):
    """Downloads the full, pre-configured MCP connection JSON file with API Bearer token."""
    auth_header = authorization or (f"Bearer {token}" if token else None)
    user_id = get_current_user_id(auth_header)
    auth_service = request.app.state.auth_service
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user account not found.",
        )
    key_data = auth_service.generate_agent_api_key(user.user_id, user.email, base_url=base_url)

    client_lower = client.lower().strip()
    if client_lower in ("claude", "claude_desktop", "claude-desktop"):
        content = key_data.claude_desktop_config_snippet
        filename = "claude_desktop_config.json"
    elif client_lower in ("cursor", "windsurf", "vscode"):
        content = key_data.cursor_config_snippet or key_data.claude_desktop_config_snippet
        filename = "mcp.json"
    else:
        content = key_data.antigravity_config_snippet
        filename = "mcp_config.json"

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
