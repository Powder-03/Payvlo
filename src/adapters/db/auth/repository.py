"""User Repository SQLAlchemy Adapter."""
from typing import Optional, List
from sqlalchemy.orm import sessionmaker
from ....domain.auth.entities import User, SavedAddress
from ....domain.auth.ports import IUserRepository
from .models import UserModel, UserAddressModel


class PostgresUserRepository(IUserRepository):
    """Platform merchant & buyer user account + address persistence using SQLAlchemy."""

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

    def _to_address_entity(self, a: UserAddressModel) -> SavedAddress:
        return SavedAddress(
            address_id=a.address_id,
            user_id=a.user_id,
            label=a.label,
            line1=a.line1,
            line2=a.line2,
            city=a.city,
            state=a.state,
            postal_code=a.postal_code,
            country=a.country,
            phone=a.phone,
            email=a.email,
            delivery_notes=a.delivery_notes,
            is_default=bool(a.is_default),
            created_at=a.created_at,
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

    def save_address(self, address: SavedAddress) -> SavedAddress:
        with self.session_factory() as session:
            # If marked default, unset other default addresses for this user
            if address.is_default:
                session.query(UserAddressModel).filter_by(user_id=address.user_id).update({"is_default": False})

            existing = session.query(UserAddressModel).filter_by(
                address_id=address.address_id
            ).first()
            if not existing:
                # Also check by (user_id, label)
                existing = session.query(UserAddressModel).filter(
                    UserAddressModel.user_id == address.user_id,
                    UserAddressModel.label.ilike(address.label.strip())
                ).first()

            if existing:
                existing.label = address.label.strip()
                existing.line1 = address.line1
                existing.line2 = address.line2
                existing.city = address.city
                existing.state = address.state
                existing.postal_code = address.postal_code
                existing.country = address.country
                existing.phone = address.phone
                existing.email = address.email
                existing.delivery_notes = address.delivery_notes
                existing.is_default = address.is_default
            else:
                m = UserAddressModel(
                    address_id=address.address_id,
                    user_id=address.user_id,
                    label=address.label.strip(),
                    line1=address.line1,
                    line2=address.line2,
                    city=address.city,
                    state=address.state,
                    postal_code=address.postal_code,
                    country=address.country,
                    phone=address.phone,
                    email=address.email,
                    delivery_notes=address.delivery_notes,
                    is_default=address.is_default,
                    created_at=address.created_at,
                )
                session.add(m)
            session.commit()
            return address

    def get_user_addresses(self, user_id: str) -> List[SavedAddress]:
        with self.session_factory() as session:
            rows = session.query(UserAddressModel).filter_by(user_id=user_id).order_by(UserAddressModel.created_at.desc()).all()
            return [self._to_address_entity(r) for r in rows]

    def get_user_address_by_label(self, user_id: str, label: str) -> Optional[SavedAddress]:
        with self.session_factory() as session:
            # Case-insensitive label match (e.g. 'home' == 'Home')
            row = session.query(UserAddressModel).filter(
                UserAddressModel.user_id == user_id,
                UserAddressModel.label.ilike(label.strip())
            ).first()
            if row:
                return self._to_address_entity(row)
            # If not found and label is 'default', check for is_default=True
            if label.strip().lower() == "default":
                def_row = session.query(UserAddressModel).filter_by(user_id=user_id, is_default=True).first()
                if def_row:
                    return self._to_address_entity(def_row)
            return None

    def delete_address(self, user_id: str, address_id: str) -> bool:
        with self.session_factory() as session:
            row = session.query(UserAddressModel).filter_by(user_id=user_id, address_id=address_id).first()
            if row:
                session.delete(row)
                session.commit()
                return True
            return False

