"""API keys (TRD 23 §4.2.6; TRD 12 SEC-020..SEC-024; FEAT-009).

Only the SHA-256 hex digest is stored (PGS-035). Keys are revoked (`active = false`), never deleted.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import ApiKey


class ApiKeyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active_by_hash(self, key_hash: str) -> ApiKey | None:
        return self.session.scalars(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.active.is_(True))
        ).first()

    def get_by_name(self, name: str) -> ApiKey | None:
        """The most recent key with this name (names are not unique in the schema)."""
        return self.session.scalars(
            select(ApiKey).where(ApiKey.name == name).order_by(ApiKey.created_at.desc())
        ).first()

    def insert(
        self,
        *,
        name: str,
        key_hash: str,
        scopes: list[str],
        device_id: uuid.UUID | None = None,
    ) -> ApiKey:
        api_key = ApiKey(name=name, key_hash=key_hash, scopes=scopes, device_id=device_id)
        self.session.add(api_key)
        self.session.flush()
        return api_key

    def upsert_by_name(self, *, name: str, key_hash: str, scopes: list[str]) -> ApiKey:
        """Seed path (DB-057): one active key per name, hash and scopes refreshed."""
        api_key = self.get_by_name(name)
        if api_key is None:
            return self.insert(name=name, key_hash=key_hash, scopes=scopes)
        api_key.key_hash = key_hash
        api_key.scopes = scopes
        api_key.active = True
        self.session.flush()
        return api_key

    def revoke(self, api_key: ApiKey) -> ApiKey:
        api_key.active = False
        self.session.flush()
        return api_key

    def touch_last_used(self, api_key: ApiKey, at: datetime) -> None:
        api_key.last_used_at = at
        self.session.flush()
