"""External Merchant Catalog APIs for BeastLife Nutrition and MuscleBlaze.

Allows merchants to sync catalog data directly without relying on external deployments.
Supports both Custom REST and Shopify-compatible /products.json payloads.
"""
from typing import Dict, Any, List
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/external-stores", tags=["External Merchant Catalog APIs"])

BEASTLIFE_PRODUCTS: List[Dict[str, Any]] = [
    {
        "id": 101,
        "sku": "BST-WHEY-001",
        "title": "Raw Whey Concentrate 80% (1kg, Unflavoured)",
        "description": "100% pure unsweetened whey protein concentrate delivering 24g clean protein and 5.5g BCAAs per scoop.",
        "body_html": "100% pure unsweetened whey protein concentrate delivering 24g clean protein and 5.5g BCAAs per scoop with zero added fillers.",
        "price": 1999.0,
        "price_inr": 1999.0,
        "inventory": 75,
        "inventory_count": 75,
        "category": "Proteins",
        "product_type": "Proteins",
        "variants": [
            {
                "id": 201,
                "sku": "BST-WHEY-001",
                "title": "Unflavoured / 1kg",
                "price": "1999.00",
                "inventory_quantity": 75,
            }
        ],
    },
    {
        "id": 102,
        "sku": "BST-WHEY-002",
        "title": "100% Beast Whey Protein (2kg, Malai Kulfi)",
        "description": "Ultra-rich whey protein blend engineered for maximum taste and rapid post-workout muscle recovery with 25g protein.",
        "body_html": "Ultra-rich whey protein blend engineered for maximum taste and rapid post-workout muscle recovery with 25g protein and DigeZyme enzymes.",
        "price": 3899.0,
        "price_inr": 3899.0,
        "inventory": 50,
        "inventory_count": 50,
        "category": "Proteins",
        "product_type": "Proteins",
        "variants": [
            {
                "id": 202,
                "sku": "BST-WHEY-002",
                "title": "Malai Kulfi / 2kg",
                "price": "3899.00",
                "inventory_quantity": 50,
            }
        ],
    },
    {
        "id": 103,
        "sku": "BST-ISO-001",
        "title": "Hyper-Whey Isolate (2kg, Chocolate Silk)",
        "description": "Ultra-filtered cross-flow microfiltered whey isolate packed with 27g ultra-fast absorbing protein.",
        "body_html": "Ultra-filtered cross-flow microfiltered whey isolate packed with 27g ultra-fast absorbing protein and virtually zero fat.",
        "price": 4999.0,
        "price_inr": 4999.0,
        "inventory": 40,
        "inventory_count": 40,
        "category": "Proteins",
        "product_type": "Proteins",
        "variants": [
            {
                "id": 203,
                "sku": "BST-ISO-001",
                "title": "Chocolate Silk / 2kg",
                "price": "4999.00",
                "inventory_quantity": 40,
            }
        ],
    },
    {
        "id": 104,
        "sku": "BST-CREAT-001",
        "title": "Creapure Micronized Creatine (250g, Unflavoured)",
        "description": "German Creapure certified 99.9% pure micronized creatine monohydrate for peak ATP resynthesis.",
        "body_html": "German Creapure certified 99.9% pure micronized creatine monohydrate for peak ATP resynthesis and explosive power.",
        "price": 999.0,
        "price_inr": 999.0,
        "inventory": 60,
        "inventory_count": 60,
        "category": "Creatine",
        "product_type": "Creatine",
        "variants": [
            {
                "id": 204,
                "sku": "BST-CREAT-001",
                "title": "Unflavoured / 250g",
                "price": "999.00",
                "inventory_quantity": 60,
            }
        ],
    },
    {
        "id": 105,
        "sku": "BST-MASS-001",
        "title": "Titan Mass High-Calorie Gainer (3kg, Belgian Chocolate)",
        "description": "Monster calorie bulk formula designed for hardgainers, delivering 52g protein and 1050 kcal per double-scoop.",
        "body_html": "Monster calorie bulk formula designed for hardgainers, delivering 52g protein and 1050 kcal per double-scoop.",
        "price": 2799.0,
        "price_inr": 2799.0,
        "inventory": 45,
        "inventory_count": 45,
        "category": "Gainers",
        "product_type": "Gainers",
        "variants": [
            {
                "id": 205,
                "sku": "BST-MASS-001",
                "title": "Belgian Chocolate / 3kg",
                "price": "2799.00",
                "inventory_quantity": 45,
            }
        ],
    },
    {
        "id": 106,
        "sku": "BST-EAA-001",
        "title": "Intra-EAA Hydro Matrix (390g, Mango Splash)",
        "description": "Complete spectrum 9 Essential Amino Acids with coconut water electrolytes for continuous intra-workout recovery.",
        "body_html": "Complete spectrum 9 Essential Amino Acids with coconut water electrolytes for continuous intra-workout recovery.",
        "price": 1599.0,
        "price_inr": 1599.0,
        "inventory": 70,
        "inventory_count": 70,
        "category": "Intra-Workout",
        "product_type": "Intra-Workout",
        "variants": [
            {
                "id": 206,
                "sku": "BST-EAA-001",
                "title": "Mango Splash / 390g",
                "price": "1599.00",
                "inventory_quantity": 70,
            }
        ],
    },
]

MUSCLEBLAZE_PRODUCTS: List[Dict[str, Any]] = [
    {
        "id": 301,
        "sku": "MB-BIO-001",
        "title": "MuscleBlaze Biozyme Performance Whey (2kg, Rich Chocolate)",
        "description": "Clinically tested Biozyme formula with 50% higher protein absorption and 25g protein per scoop.",
        "body_html": "Clinically tested Biozyme formula with 50% higher protein absorption and 25g protein per scoop, verified by lab door certifications.",
        "price": 4699.0,
        "price_inr": 4699.0,
        "inventory": 55,
        "inventory_count": 55,
        "category": "Proteins",
        "product_type": "Proteins",
        "variants": [
            {
                "id": 401,
                "sku": "MB-BIO-001",
                "title": "Rich Chocolate / 2kg",
                "price": "4699.00",
                "inventory_quantity": 55,
            }
        ],
    },
    {
        "id": 302,
        "sku": "MB-RAW-001",
        "title": "MuscleBlaze Raw Whey Protein 80% (1kg, Unflavoured)",
        "description": "100% unsweetened raw whey concentrate delivering 24g pure protein per serving with zero additives.",
        "body_html": "100% unsweetened raw whey concentrate delivering 24g pure protein per serving with zero artificial colors, sweeteners, or flavorings.",
        "price": 1899.0,
        "price_inr": 1899.0,
        "inventory": 80,
        "inventory_count": 80,
        "category": "Proteins",
        "product_type": "Proteins",
        "variants": [
            {
                "id": 402,
                "sku": "MB-RAW-001",
                "title": "Unflavoured / 1kg",
                "price": "1899.00",
                "inventory_quantity": 80,
            }
        ],
    },
    {
        "id": 303,
        "sku": "MB-ISO-001",
        "title": "MuscleBlaze Biozyme Whey Isolate (2kg, Cafe Mocha)",
        "description": "Ultra-pure whey isolate with 27g protein, low carbs, and enhanced digestive enzyme formulation.",
        "body_html": "Ultra-pure whey isolate with 27g protein, low carbs, and enhanced digestive enzyme formulation for rapid absorption.",
        "price": 5499.0,
        "price_inr": 5499.0,
        "inventory": 30,
        "inventory_count": 30,
        "category": "Proteins",
        "product_type": "Proteins",
        "variants": [
            {
                "id": 403,
                "sku": "MB-ISO-001",
                "title": "Cafe Mocha / 2kg",
                "price": "5499.00",
                "inventory_quantity": 30,
            }
        ],
    },
    {
        "id": 304,
        "sku": "MB-CREAT-001",
        "title": "MuscleBlaze Creatine Monohydrate (100g, Unflavoured)",
        "description": "Fast-absorbing micronized creatine monohydrate to fuel strength, power, and athletic endurance.",
        "body_html": "Fast-absorbing micronized creatine monohydrate to fuel strength, power, and athletic endurance with zero adulteration.",
        "price": 549.0,
        "price_inr": 549.0,
        "inventory": 110,
        "inventory_count": 110,
        "category": "Creatine",
        "product_type": "Creatine",
        "variants": [
            {
                "id": 404,
                "sku": "MB-CREAT-001",
                "title": "Unflavoured / 100g",
                "price": "549.00",
                "inventory_quantity": 110,
            }
        ],
    },
    {
        "id": 305,
        "sku": "MB-MASS-001",
        "title": "MuscleBlaze Super Gainer XXL (3kg, Chocolate)",
        "description": "Advanced high-protein mass gainer with a clean 1:5 protein to carb ratio for healthy lean weight gain.",
        "body_html": "Advanced high-protein mass gainer with a clean 1:5 protein to carb ratio for healthy lean weight gain and muscle hypertrophy.",
        "price": 2499.0,
        "price_inr": 2499.0,
        "inventory": 40,
        "inventory_count": 40,
        "category": "Gainers",
        "product_type": "Gainers",
        "variants": [
            {
                "id": 405,
                "sku": "MB-MASS-001",
                "title": "Chocolate / 3kg",
                "price": "2499.00",
                "inventory_quantity": 40,
            }
        ],
    },
    {
        "id": 306,
        "sku": "MB-PRE-001",
        "title": "MuscleBlaze Pre-Workout 200 (100g, Fruit Punch)",
        "description": "Intense explosive energy booster with 200mg caffeine, 2200mg beta-alanine, and 1500mg L-citrulline.",
        "body_html": "Intense explosive energy booster with 200mg caffeine, 2200mg beta-alanine, and 1500mg L-citrulline for razor-sharp workout focus.",
        "price": 799.0,
        "price_inr": 799.0,
        "inventory": 85,
        "inventory_count": 85,
        "category": "Pre-Workout",
        "product_type": "Pre-Workout",
        "variants": [
            {
                "id": 406,
                "sku": "MB-PRE-001",
                "title": "Fruit Punch / 100g",
                "price": "799.00",
                "inventory_quantity": 85,
            }
        ],
    },
]


@router.get("/beastlife/products")
@router.get("/beastlife/products.json")
def get_beastlife_catalog():
    """Returns BeastLife Nutrition catalog for synchronization."""
    return {
        "store": "beastlife_d2c",
        "brand": "BeastLife Performance Nutrition",
        "currency": "INR",
        "total_items": len(BEASTLIFE_PRODUCTS),
        "products": BEASTLIFE_PRODUCTS,
    }


@router.get("/muscleblaze/products")
@router.get("/muscleblaze/products.json")
@router.get("/muscles/products")
@router.get("/muscles/products.json")
def get_muscleblaze_catalog():
    """Returns MuscleBlaze Nutrition catalog for synchronization."""
    return {
        "store": "muscleblaze",
        "brand": "MuscleBlaze Performance Nutrition",
        "currency": "INR",
        "total_items": len(MUSCLEBLAZE_PRODUCTS),
        "products": MUSCLEBLAZE_PRODUCTS,
    }
