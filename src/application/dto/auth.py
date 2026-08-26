"""User Authentication and Merchant Portal DTOs.

Clean Architecture layer: Application.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr
from .catalog import ProductDTO
from .merchant import MerchantProfileDTO


class UserSignupInputDTO(BaseModel):
    email: str = Field(..., description="Valid user email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    full_name: str = Field(..., min_length=1, description="User full name")
    company_name: str = Field(..., min_length=1, description="Company or Brand name")


class UserLoginInputDTO(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Account password")


class UserProfileDTO(BaseModel):
    user_id: str
    email: str
    full_name: str
    company_name: str
    created_at: str


class UserAuthResponseDTO(BaseModel):
    success: bool
    token: str
    token_type: str = "bearer"
    user: UserProfileDTO
    has_store: bool = False
    merchant_id: Optional[str] = None
    message: str


class MyStoreResponseDTO(BaseModel):
    has_store: bool
    merchant: Optional[MerchantProfileDTO] = None
    total_products: int = 0
    agent_card_url: Optional[str] = None
    products: List[ProductDTO] = Field(default_factory=list)
