"""Product Catalog Domain Entities."""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Product:
    """Represents an item in the merchant's catalog."""
    product_id: str
    merchant_id: str
    sku: str
    title: str
    description: str
    price_inr: float
    inventory_count: int
    category: str
    max_discount_percentage: float = 0.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_available(self, requested_quantity: int = 1) -> bool:
        """Checks if sufficient inventory is in stock."""
        return self.inventory_count >= requested_quantity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "merchant_id": self.merchant_id,
            "sku": self.sku,
            "title": self.title,
            "description": self.description,
            "price_inr": self.price_inr,
            "inventory_count": self.inventory_count,
            "category": self.category,
            "max_discount_percentage": self.max_discount_percentage,
            "tags": self.tags,
            "metadata": self.metadata,
        }
