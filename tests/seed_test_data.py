"""Standalone Test & Demo Environment Seeder.

Location: tests/seed_test_data.py
Populates mock merchants, sample products, and demo user credentials for testing.
"""
import sys
import os
import json
import uuid
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import sessionmaker

from src.infrastructure.config import settings
from src.infrastructure.database import create_db_engine, init_database
from src.domain.entities import MerchantProfile, Product, User
from src.adapters.postgres_repo import (
    ProductModel,
    MerchantModel,
    UserModel,
    PostgresCatalogRepository,
    PostgresUserRepository,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestSeeder")


def seed_test_environment(database_url: str = None):
    db_url = database_url or os.getenv("DATABASE_URL", settings.DATABASE_URL)
    engine, session_factory, catalog_repo, audit_repo, user_repo = init_database(db_url)

    logger.info(f"🌱 Seeding test environment into database ({db_url})...")

    # =========================================================================
    # 1. Demo User Accounts
    # =========================================================================
    demo_user_1 = user_repo.get_user_by_email("demo@payvlo.com")
    if not demo_user_1:
        salt_1 = uuid.uuid4().hex[:16]
        user_repo.save_user(User(
            user_id="usr_demo_dominos",
            email="demo@payvlo.com",
            password_hash=User.hash_password("password123", salt_1),
            salt=salt_1,
            full_name="Rajesh Sharma (Domino's Admin)",
            company_name="Domino's Pizza India",
        ))
        logger.info("  👤 Created demo user: demo@payvlo.com / password123")

    demo_user_2 = user_repo.get_user_by_email("fitness@payvlo.com")
    if not demo_user_2:
        salt_2 = uuid.uuid4().hex[:16]
        user_repo.save_user(User(
            user_id="usr_fitness_beastlife",
            email="fitness@payvlo.com",
            password_hash=User.hash_password("password123", salt_2),
            salt=salt_2,
            full_name="Ananya Verma (BeastLife Admin)",
            company_name="BeastLife Performance Nutrition",
        ))
        logger.info("  👤 Created demo user: fitness@payvlo.com / password123")

    # =========================================================================
    # 2. Domino's Pizza India (Food & Beverage)
    # =========================================================================
    dominos_profile = MerchantProfile(
        merchant_id="dominos_in",
        merchant_name="Domino's Pizza India",
        category="Food & Beverage",
        currency="INR",
        max_discount_percentage=15.0,
        per_tx_spend_cap=5000.0,
        daily_merchant_spend_cap=500000.0,
        allowed_payment_methods=["upi", "card", "netbanking", "wallet"],
        support_email="guestcare@dominos.in",
        owner_user_id="usr_demo_dominos",
        metadata={"delivery_guarantee_minutes": 30, "serviceable_country": "IN"},
    )
    catalog_repo.save_merchant(dominos_profile)

    dominos_products = [
        Product(
            product_id="DOM-PIZ-001",
            merchant_id="dominos_in",
            sku="DOM-PIZ-001",
            title="Farmhouse Veg Pizza (Medium, Cheese Burst)",
            description="Delightful combination of onion, capsicum, tomato, and grilled mushroom on fresh dough.",
            price_inr=459.0,
            inventory_count=100,
            category="Pizzas",
            max_discount_percentage=15.0,
            tags=["pizza", "veg", "cheese-burst", "bestseller"],
            metadata={"calories": 850, "serves": 2},
        ),
        Product(
            product_id="DOM-PIZ-002",
            merchant_id="dominos_in",
            sku="DOM-PIZ-002",
            title="Pepper Barbecue Chicken Pizza (Medium)",
            description="Pepper barbecue chicken for that extra flavorful kick with 100% mozzarella cheese.",
            price_inr=549.0,
            inventory_count=80,
            category="Pizzas",
            max_discount_percentage=15.0,
            tags=["pizza", "non-veg", "chicken", "barbecue"],
            metadata={"calories": 920, "serves": 2},
        ),
        Product(
            product_id="DOM-SD-001",
            merchant_id="dominos_in",
            sku="DOM-SD-001",
            title="Garlic Breadsticks with Cheesy Dip",
            description="Baked to perfection garlic breadsticks accompanied by creamy jalapeño cheesy dip.",
            price_inr=149.0,
            inventory_count=200,
            category="Sides",
            max_discount_percentage=10.0,
            tags=["sides", "garlic-bread", "snack"],
            metadata={"calories": 350},
        ),
        Product(
            product_id="DOM-DS-001",
            merchant_id="dominos_in",
            sku="DOM-DS-001",
            title="Choco Lava Cake",
            description="Indulgent chocolate cake with molten liquid chocolate core.",
            price_inr=109.0,
            inventory_count=150,
            category="Desserts",
            max_discount_percentage=10.0,
            tags=["dessert", "chocolate", "sweet"],
            metadata={"calories": 380},
        ),
    ]

    for p in dominos_products:
        if not catalog_repo.get_product("dominos_in", p.product_id):
            with session_factory() as session:
                session.add(
                    ProductModel(
                        product_id=p.product_id,
                        merchant_id=p.merchant_id,
                        sku=p.sku,
                        title=p.title,
                        description=p.description,
                        price_inr=p.price_inr,
                        inventory_count=p.inventory_count,
                        category=p.category,
                        max_discount_percentage=p.max_discount_percentage,
                        tags_json=json.dumps(p.tags),
                        metadata_json=json.dumps(p.metadata),
                    )
                )
                session.commit()

    # =========================================================================
    # 3. BeastLife D2C (Fitness, Nutrition & Supplements)
    # =========================================================================
    beastlife_profile = MerchantProfile(
        merchant_id="beastlife_d2c",
        merchant_name="BeastLife Performance Nutrition",
        category="D2C Health & Fitness",
        currency="INR",
        max_discount_percentage=20.0,
        per_tx_spend_cap=25000.0,
        daily_merchant_spend_cap=1000000.0,
        allowed_payment_methods=["upi", "card", "netbanking", "emi"],
        support_email="support@beastlife.fit",
        owner_user_id="usr_fitness_beastlife",
        metadata={"brand": "BeastLife", "origin": "India"},
    )
    catalog_repo.save_merchant(beastlife_profile)

    beastlife_products = [
        Product(
            product_id="BST-PRT-001",
            merchant_id="beastlife_d2c",
            sku="BST-PRT-001",
            title="Hyper-Whey Isolate Protein (Chocolate Silk 2kg)",
            description="100% Pure Whey Protein Isolate, 27g Protein per scoop, Zero added sugar.",
            price_inr=4999.0,
            inventory_count=50,
            category="Protein",
            max_discount_percentage=20.0,
            tags=["whey", "protein", "isolate", "fitness"],
            metadata={"servings": 66, "flavour": "Chocolate Silk"},
        ),
        Product(
            product_id="BST-CRT-001",
            merchant_id="beastlife_d2c",
            sku="BST-CRT-001",
            title="Micronized Creatine Monohydrate (250g)",
            description="Ultra-pure micronized creatine monohydrate for explosive power and muscle strength.",
            price_inr=999.0,
            inventory_count=120,
            category="Performance",
            max_discount_percentage=15.0,
            tags=["creatine", "strength", "power", "unflavoured"],
            metadata={"servings": 83},
        ),
    ]

    for p in beastlife_products:
        if not catalog_repo.get_product("beastlife_d2c", p.product_id):
            with session_factory() as session:
                session.add(
                    ProductModel(
                        product_id=p.product_id,
                        merchant_id=p.merchant_id,
                        sku=p.sku,
                        title=p.title,
                        description=p.description,
                        price_inr=p.price_inr,
                        inventory_count=p.inventory_count,
                        category=p.category,
                        max_discount_percentage=p.max_discount_percentage,
                        tags_json=json.dumps(p.tags),
                        metadata_json=json.dumps(p.metadata),
                    )
                )
                session.commit()

    logger.info("✅ Test environment preseeded successfully!")
    logger.info("   • Domino's India: dominos_in (Login: demo@payvlo.com / password123)")
    logger.info("   • BeastLife D2C: beastlife_d2c (Login: fitness@payvlo.com / password123)")


if __name__ == "__main__":
    seed_test_environment()
