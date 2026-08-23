"""Database Engine, Session Management, and Schema Migration.

Clean Architecture layer: Infrastructure.
Handles PostgreSQL (Neon Serverless / Docker) and local SQLite schemas.
Zero test data or mock seeders.
"""
import logging
from typing import Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from ..adapters.postgres_repo import (
    Base,
    PostgresCatalogRepository,
    PostgresAuditRepository,
    PostgresUserRepository,
)

logger = logging.getLogger("Database")


def create_db_engine(database_url: str):
    """Creates SQLAlchemy engine with appropriate dialect arguments."""
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    elif database_url.startswith("postgresql"):
        # Neon / Docker PostgreSQL pooling
        pass

    engine = create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
    return engine


def _auto_migrate_schema(engine):
    """Safely adds new columns to existing PostgreSQL / SQLite tables on startup."""
    try:
        with engine.connect() as conn:
            if engine.dialect.name == "postgresql":
                conn.execute(text("ALTER TABLE merchants ADD COLUMN IF NOT EXISTS sync_config_json TEXT DEFAULT '{}'"))
                conn.execute(text("ALTER TABLE merchants ADD COLUMN IF NOT EXISTS owner_user_id VARCHAR(64)"))
                conn.commit()
            elif engine.dialect.name == "sqlite":
                try:
                    conn.execute(text("ALTER TABLE merchants ADD COLUMN sync_config_json TEXT DEFAULT '{}'"))
                except Exception:
                    pass
                try:
                    conn.execute(text("ALTER TABLE merchants ADD COLUMN owner_user_id VARCHAR(64)"))
                except Exception:
                    pass
                conn.commit()
    except Exception as e:
        logger.debug(f"Schema auto-migration notice: {e}")


def init_database(database_url: str):
    """Initializes tables and returns sessionmaker and all repository instances."""
    engine = create_db_engine(database_url)
    Base.metadata.create_all(bind=engine)
    _auto_migrate_schema(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    catalog_repo = PostgresCatalogRepository(session_factory)
    audit_repo = PostgresAuditRepository(session_factory)
    user_repo = PostgresUserRepository(session_factory)

    return engine, session_factory, catalog_repo, audit_repo, user_repo
