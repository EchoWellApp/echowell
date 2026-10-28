"""Users (TRD 23 §4.2.2; TRD 12 SEC-016, SEC-125; FEAT-009).

E-mails are trimmed and lower-cased before lookup and storage (SEC-016). Users are deactivated,
never deleted (PGS-021).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import User, UserRole


def normalise_email(email: str) -> str:
    """Trimmed, lower-case e-mail (SEC-016)."""
    return email.strip().lower()


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalars(
            select(User).where(User.email == normalise_email(email))
        ).first()

    def list_page(self, *, limit: int = 50, offset: int = 0) -> tuple[list[User], int]:
        """Users ordered by e-mail with the total count (API-016 paging)."""
        total = self.session.scalar(select(func.count()).select_from(User)) or 0
        rows = self.session.scalars(
            select(User).order_by(User.email).limit(limit).offset(offset)
        ).all()
        return list(rows), total

    def insert(self, *, email: str, display_name: str, password_hash: str, role: UserRole) -> User:
        user = User(
            email=normalise_email(email),
            display_name=display_name,
            password_hash=password_hash,
            role=role,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def update(
        self,
        user: User,
        *,
        display_name: str | None = None,
        role: UserRole | None = None,
        active: bool | None = None,
        password_hash: str | None = None,
    ) -> User:
        if display_name is not None:
            user.display_name = display_name
        if role is not None:
            user.role = role
        if active is not None:
            user.active = active
        if password_hash is not None:
            user.password_hash = password_hash
        self.session.flush()
        return user

    def touch_login(self, user: User, at: datetime) -> None:
        user.last_login_at = at
        self.session.flush()
