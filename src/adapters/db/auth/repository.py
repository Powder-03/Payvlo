"""User Repository SQLAlchemy Adapter."""
from typing import Optional
from sqlalchemy.orm import sessionmaker
from ....domain.auth.entities import User
from ....domain.auth.ports import IUserRepository
from .models import UserModel


class PostgresUserRepository(IUserRepository):
    """Platform merchant user account persistence using SQLAlchemy."""

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def _to_user_entity(self, u: UserModel) -> User:
        return User(
            user_id=u.user_id,
            email=u.email,
            password_hash=u.password_hash,
            salt=u.salt,
            full_name=u.full_name,
            company_name=u.company_name,
            created_at=u.created_at,
        )

    def get_user_by_email(self, email: str) -> Optional[User]:
        with self.session_factory() as session:
            u = session.query(UserModel).filter_by(email=email.strip().lower()).first()
            return self._to_user_entity(u) if u else None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        with self.session_factory() as session:
            u = session.query(UserModel).filter_by(user_id=user_id).first()
            return self._to_user_entity(u) if u else None

    def save_user(self, user: User) -> None:
        with self.session_factory() as session:
            existing = session.query(UserModel).filter_by(user_id=user.user_id).first()
            if existing:
                existing.email = user.email.strip().lower()
                existing.password_hash = user.password_hash
                existing.salt = user.salt
                existing.full_name = user.full_name
                existing.company_name = user.company_name
            else:
                u = UserModel(
                    user_id=user.user_id,
                    email=user.email.strip().lower(),
                    password_hash=user.password_hash,
                    salt=user.salt,
                    full_name=user.full_name,
                    company_name=user.company_name,
                    created_at=user.created_at,
                )
                session.add(u)
            session.commit()
