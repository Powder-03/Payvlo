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
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config import settings
from src.core.database import init_database
from src.models import (
    Base,
    ProductModel,
    MerchantModel,
    UserModel,
)
from src.services.auth_service import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DataSeeder")

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def load_json_file(filename: str):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_test_environment(database_url: str = None, reset: bool = True):
    db_url = database_url or os.getenv("DATABASE_URL", settings.DATABASE_URL)
    engine, session_factory = init_database(db_url)

    if reset:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    logger.info(f"🌱 Loading seed inventory & merchant data from {DATA_DIR}...")
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 1. Load & Seed Users
    users_data = load_json_file("users.json")
    with session_factory() as session:
        for u in users_data:
            existing = session.query(UserModel).filter_by(email=u["email"]).first()
            if not existing:
                salt = uuid.uuid4().hex[:16]
                session.add(
                    UserModel(
                        user_id=u["user_id"],
                        email=u["email"],
                        password_hash=hash_password(u["password"], salt),
                        salt=salt,
                        full_name=u["full_name"],
                        company_name=u["company_name"],
                        created_at=now_str,
                    )
                )
                logger.info(f"   👤 User created: {u['email']} (Password: {u['password']})")
        session.commit()

    # 2. Load & Seed Merchants
    merchants_data = load_json_file("merchants.json")
    with session_factory() as session:
        for m in merchants_data:
            existing = session.query(MerchantModel).filter_by(merchant_id=m["merchant_id"]).first()
            if not existing:
                session.add(
                    MerchantModel(
                        merchant_id=m["merchant_id"],
                        merchant_name=m["merchant_name"],
                        category=m["category"],
                        currency=m.get("currency", "INR"),
                        max_discount_percentage=m.get("max_discount_percentage", 15.0),
                        per_tx_spend_cap=m.get("per_tx_spend_cap", 10000.0),
                        daily_merchant_spend_cap=m.get("daily_merchant_spend_cap", 500000.0),
                        allowed_payment_methods_json=json.dumps(m.get("allowed_payment_methods", ["upi", "card"])),
                        support_email=m.get("support_email", "support@merchant.com"),
                        owner_user_id=m.get("owner_user_id"),
                        metadata_json=json.dumps(m.get("metadata", {})),
                    )
                )
                logger.info(f"   🏪 Merchant profile saved: {m['merchant_name']} ({m['merchant_id']})")
        session.commit()

    # 3. Load & Seed Products
    products_data = load_json_file("products.json")
    with session_factory() as session:
        for p in products_data:
            existing_p = (
                session.query(ProductModel)
                .filter_by(merchant_id=p["merchant_id"], product_id=p["product_id"])
                .first()
            )
            if not existing_p:
                session.add(
                    ProductModel(
                        product_id=p["product_id"],
                        merchant_id=p["merchant_id"],
                        sku=p["sku"],
                        title=p["title"],
                        description=p.get("description", ""),
                        price_inr=float(p["price_inr"]),
                        inventory_count=int(p.get("inventory_count", 10)),
                        category=p["category"],
                        max_discount_percentage=float(p.get("max_discount_percentage", 0.0)),
                        tags_json=json.dumps(p.get("tags", [])),
                        metadata_json=json.dumps(p.get("metadata", {})),
                    )
                )
        session.commit()

    logger.info(
        f"✅ Seeding complete: {len(merchants_data)} merchants, {len(products_data)} products, {len(users_data)} users loaded."
    )
