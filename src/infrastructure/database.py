"""Database Engine, Session Management, and Multi-Merchant Seeder.

Clean Architecture layer: Infrastructure.
Handles PostgreSQL (Neon Serverless) and local SQLite schemas and dynamic seeds.
"""
import logging
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..domain.entities import MerchantProfile, Product
from ..adapters.postgres_repo import (
    Base,
    PostgresCatalogRepository,
    PostgresAuditRepository,
)

logger = logging.getLogger("Database")


def create_db_engine(database_url: str):
    """Creates SQLAlchemy engine with appropriate dialect arguments."""
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    elif database_url.startswith("postgresql"):
        # Neon PostgreSQL serverless pooling
        pass

    engine = create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
    return engine


def init_database(database_url: str):
    """Initializes tables and returns sessionmaker and repositories."""
    engine = create_db_engine(database_url)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    catalog_repo = PostgresCatalogRepository(session_factory)
    audit_repo = PostgresAuditRepository(session_factory)

    return engine, session_factory, catalog_repo, audit_repo


def seed_merchants_and_catalog(catalog_repo: PostgresCatalogRepository):
    """Seeds multi-merchant profiles and catalog products for Domino's, BeastLife, Havells."""
    logger.info("Checking and seeding multi-merchant catalog data...")

    # =========================================================================
    # 1. Domino's Pizza (Food & Beverage)
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
        Product(
            product_id="DOM-BV-001",
            merchant_id="dominos_in",
            sku="DOM-BV-001",
            title="Pepsi 500ml Pet Bottle",
            description="Refreshing chilled carbonated beverage.",
            price_inr=60.0,
            inventory_count=300,
            category="Beverages",
            max_discount_percentage=5.0,
            tags=["beverage", "drink", "cold"],
            metadata={"calories": 210},
        ),
    ]

    for p in dominos_products:
        if not catalog_repo.get_product("dominos_in", p.product_id):
            with catalog_repo.session_factory() as session:
                from ..adapters.postgres_repo import ProductModel
                import json
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
    # 2. BeastLife D2C (Fitness, Nutrition & Supplements)
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
        metadata={"brand": "BeastLife", "origin": "India"},
    )
    catalog_repo.save_merchant(beastlife_profile)

    beastlife_products = [
        Product(
            product_id="BST-PRT-001",
            merchant_id="beastlife_d2c",
            sku="BST-PRT-001",
            title="Hyper-Whey Isolate Protein (Chocolate Silk 2kg)",
            description="100% Pure Whey Protein Isolate, 27g Protein per scoop, Zero added sugar, Ultra-filtered.",
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
            title="Creatine Monohydrate Micronized (300g, Unflavored)",
            description="Creapure pharmaceutical grade micronized creatine for explosive power and muscle volume.",
            price_inr=999.0,
            inventory_count=100,
            category="Performance",
            max_discount_percentage=15.0,
            tags=["creatine", "strength", "muscle"],
            metadata={"servings": 100},
        ),
        Product(
            product_id="BST-PWO-001",
            merchant_id="beastlife_d2c",
            sku="BST-PWO-001",
            title="Pre-Workout Nitro Blast (Fruit Punch 300g)",
            description="High-stimulant pre-workout formula with 300mg Caffeine, Beta-Alanine, and L-Citrulline.",
            price_inr=1499.0,
            inventory_count=60,
            category="Performance",
            max_discount_percentage=15.0,
            tags=["pre-workout", "energy", "caffeine"],
            metadata={"servings": 30},
        ),
        Product(
            product_id="BST-ACC-001",
            merchant_id="beastlife_d2c",
            sku="BST-ACC-001",
            title="Anabolic Pro Shaker Bottle (700ml, Matte Black)",
            description="Leak-proof stainless steel agitator shaker bottle, BPA free.",
            price_inr=399.0,
            inventory_count=150,
            category="Accessories",
            max_discount_percentage=25.0,
            tags=["shaker", "bottle", "gear"],
            metadata={"capacity_ml": 700},
        ),
    ]

    for p in beastlife_products:
        if not catalog_repo.get_product("beastlife_d2c", p.product_id):
            with catalog_repo.session_factory() as session:
                from ..adapters.postgres_repo import ProductModel
                import json
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
    # 3. Havells Consumer Tech (Smart Home & Electronics)
    # =========================================================================
    havells_profile = MerchantProfile(
        merchant_id="havells_tech",
        merchant_name="Havells Consumer Tech",
        category="Consumer Electricals & IoT",
        currency="INR",
        max_discount_percentage=12.0,
        per_tx_spend_cap=50000.0,
        daily_merchant_spend_cap=2000000.0,
        allowed_payment_methods=["upi", "card", "netbanking", "emi"],
        support_email="customercare@havells.com",
        metadata={"warranty_support": True, "country": "IN"},
    )
    catalog_repo.save_merchant(havells_profile)

    havells_products = [
        Product(
            product_id="HAV-FAN-001",
            merchant_id="havells_tech",
            sku="HAV-FAN-001",
            title="Havells Stealth Air Ceiling Fan (1200mm Indigo Blue)",
            description="Ultra-quiet BLDC motor energy efficient smart ceiling fan with remote control.",
            price_inr=5299.0,
            inventory_count=30,
            category="Appliances",
            max_discount_percentage=12.0,
            tags=["fan", "bldc", "appliance", "smart-home"],
            metadata={"warranty_years": 2, "power_watts": 28},
        ),
        Product(
            product_id="HAV-APL-001",
            merchant_id="havells_tech",
            sku="HAV-APL-001",
            title="Havells HD3151 Foldable Hair Dryer (1200W)",
            description="Quick dry gentle styling hair dryer with dual heat settings and cool air shot.",
            price_inr=1199.0,
            inventory_count=45,
            category="Personal Care",
            max_discount_percentage=15.0,
            tags=["grooming", "hair-dryer", "appliances"],
            metadata={"warranty_years": 2},
        ),
        Product(
            product_id="HAV-IOT-001",
            merchant_id="havells_tech",
            sku="HAV-IOT-001",
            title="Havells Crabtree Smart WiFi Touch Switch (4 Gang)",
            description="Smart home automation touch panel compatible with Alexa, Google Home, and Mobile App.",
            price_inr=2799.0,
            inventory_count=80,
            category="Smart Home",
            max_discount_percentage=10.0,
            tags=["iot", "switch", "smart-home", "automation"],
            metadata={"voltage": "230V AC"},
        ),
    ]

    for p in havells_products:
        if not catalog_repo.get_product("havells_tech", p.product_id):
            with catalog_repo.session_factory() as session:
                from ..adapters.postgres_repo import ProductModel
                import json
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

    logger.info("Catalog seeder completed successfully for Domino's, BeastLife, and Havells.")
