"""Authentication, User Profile, and Saved Address Schemas."""
from typing import List, Optional
from pydantic import BaseModel, Field
from .catalog import ProductSchema, MerchantProfileSchema


class UserSignupInputSchema(BaseModel):
    email: str = Field(..., description="Valid user email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    full_name: str = Field(..., min_length=1, description="User full name")
    company_name: Optional[str] = Field(
        default="", description="Company or Brand name (optional for buyers)"
    )
    persona: Optional[str] = Field(
        default="buyer", description="User persona: 'merchant' or 'buyer'"
    )


UserSignupInputDTO = UserSignupInputSchema


class UserLoginInputSchema(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Account password")


UserLoginInputDTO = UserLoginInputSchema


class UserProfileSchema(BaseModel):
    user_id: str
    email: str
    full_name: str
    company_name: str
    created_at: str


UserProfileDTO = UserProfileSchema


class UserAuthResponseSchema(BaseModel):
    success: bool
    token: str
    token_type: str = "bearer"
    user: UserProfileSchema
    has_store: bool = False
    merchant_id: Optional[str] = None
    message: str


UserAuthResponseDTO = UserAuthResponseSchema


class SavedAddressInputSchema(BaseModel):
    label: str = Field(
        ..., min_length=1, description="Address nickname (e.g. 'Home', 'Work')"
    )
    line1: str = Field(
        ..., min_length=1, description="Street address, building, flat number"
    )
    line2: Optional[str] = Field(default=None, description="Apartment, suite, landmark")
    city: str = Field(default="Bengaluru", description="City")
    state: str = Field(default="KA", description="State code or name")
    postal_code: str = Field(default="560001", description="Postal / ZIP code")
    country: str = Field(default="IN", description="Country code")
    phone: Optional[str] = Field(default=None, description="Contact phone number")
    email: Optional[str] = Field(default=None, description="Contact email")
    delivery_notes: Optional[str] = Field(
        default=None, description="Delivery or table notes"
    )
    is_default: bool = Field(default=False, description="Set as default address")


SavedAddressInputDTO = SavedAddressInputSchema


class SavedAddressResponseSchema(BaseModel):
    address_id: str
    user_id: str
    label: str
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str
    phone: Optional[str] = None
    email: Optional[str] = None
    delivery_notes: Optional[str] = None
    is_default: bool
    created_at: str


SavedAddressResponseDTO = SavedAddressResponseSchema


class UserApiKeyResponseSchema(BaseModel):
    user_id: str
    email: str
    api_key: str
    token_type: str = "Bearer"
    mcp_server_url: str
    expires_in_days: int = 365
    antigravity_config_snippet: str
    claude_desktop_config_snippet: str


UserApiKeyResponseDTO = UserApiKeyResponseSchema


class MyStoreResponseSchema(BaseModel):
    has_store: bool
    merchant: Optional[MerchantProfileSchema] = None
    total_products: int = 0
    agent_card_url: Optional[str] = None
    products: List[ProductSchema] = Field(default_factory=list)


MyStoreResponseDTO = MyStoreResponseSchema
