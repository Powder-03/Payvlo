"""Catalog and Product DTOs.

Clean Architecture layer: Application.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class ProductDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    merchant_id: str
    sku: str
    title: str
    description: str
    price_inr: float
    inventory_count: int
    category: str
    max_discount_percentage: float = 0.0
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CatalogSearchInputDTO(BaseModel):
    query: Optional[str] = Field(
        default=None, description="Keywords to match in title, description, or tags"
    )
    category: Optional[str] = Field(
        default=None, description="Filter products by merchant category"
    )
    min_price: Optional[float] = Field(
        default=None, description="Minimum price in INR"
    )
    max_price: Optional[float] = Field(
        default=None, description="Maximum price in INR"
    )
    merchant_id: Optional[str] = Field(
        default=None, description="Specific merchant ID"
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class CatalogSearchResultDTO(BaseModel):
    merchant_id: str
    total_count: int
    products: List[ProductDTO]


class DirectProductInputDTO(BaseModel):
    sku: str
    title: str
    description: Optional[str] = ""
    price_inr: float = Field(..., gt=0.0)
    inventory_count: int = Field(default=10, ge=0)
    category: str = "General"
    max_discount_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
