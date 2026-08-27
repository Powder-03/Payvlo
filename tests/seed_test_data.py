"""Automated Loader for Seed JSON Data.

Location: tests/seed_test_data.py
Loads merchants, products, and user accounts directly from:
- data/merchants.json
- data/products.json
- data/users.json
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
from src.domain.merchant import MerchantProfile
from src.domain.catalog import Product
from src.domain.auth import User
from src.adapters.db import (
    Base,
    ProductModel,
    MerchantModel,
    UserModel,
    PostgresCatalogRepository,
    PostgresUserRepository,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DataSeeder")

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def load_json_file(filename: str):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_test_environment(database_url: str = None, reset: bool = True):
    db_url = database_url or os.getenv("DATABASE_URL", settings.DATABASE_URL)
    engine, session_factory, catalog_repo, audit_repo, user_repo = init_database(db_url)

    if reset:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    logger.info(f"🌱 Loading seed inventory & merchant data from {DATA_DIR}...")

    # 1. Load & Seed Users
    users_data = load_json_file("users.json")
    for u in users_data:
        existing = user_repo.get_user_by_email(u["email"])
        if not existing:
            salt = uuid.uuid4().hex[:16]
            user_repo.save_user(User(
                user_id=u["user_id"],
                email=u["email"],
                password_hash=User.hash_password(u["password"], salt),
                salt=salt,
                full_name=u["full_name"],
                company_name=u["company_name"],
            ))
            logger.info(f"   👤 User created: {u['email']} (Password: {u['password']})")

    # 2. Load & Seed Merchants
    merchants_data = load_json_file("merchants.json")
    for m in merchants_data:
        profile = MerchantProfile(
            merchant_id=m["merchant_id"],
            merchant_name=m["merchant_name"],
            category=m["category"],
            currency=m.get("currency", "INR"),
            max_discount_percentage=m.get("max_discount_percentage", 15.0),
            per_tx_spend_cap=m.get("per_tx_spend_cap", 10000.0),
            daily_merchant_spend_cap=m.get("daily_merchant_spend_cap", 500000.0),
            allowed_payment_methods=m.get("allowed_payment_methods", ["upi", "card"]),
            support_email=m.get("support_email", "support@merchant.com"),
            owner_user_id=m.get("owner_user_id"),
            metadata=m.get("metadata", {}),
        )
        catalog_repo.save_merchant(profile)
        logger.info(f"   🏪 Merchant profile saved: {m['merchant_name']} ({m['merchant_id']})")

    # 3. Load & Seed Products
    products_data = load_json_file("products.json")
    for p in products_data:
        existing_p = catalog_repo.get_product(p["merchant_id"], p["product_id"])
        if not existing_p:
            with session_factory() as session:
                session.add(
                    ProductModel(
                        product_id=p["product_id"],
                        merchant_id=p["merchant_id"],
                        sku=p["sku"],
                        title=p["title"],
                        description=p.get("description", ""),
                        price_inr=p["price_inr"],
                        inventory_count=p.get("inventory_count", 50),
                        category=p.get("category", "General"),
                        max_discount_percentage=p.get("max_discount_percentage", 0.0),
                        tags_json=json.dumps(p.get("tags", [])),
                        metadata_json=json.dumps(p.get("metadata", {})),
                    )
                )
                session.commit()

    logger.info(f"✅ Seeding complete: {len(merchants_data)} merchants, {len(products_data)} products, {len(users_data)} users loaded.")


if __name__ == "__main__":
    seed_test_environment()
