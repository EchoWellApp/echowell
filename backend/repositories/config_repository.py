"""Config parameters (TRD 23 §4.2.22; TRD 20 §4.11; FEAT-009).

Rows are seeded by migration 0002. No endpoint writes them; `update_value` is for the `set-config`
operator command, which runs as `echowell_migrator` (FR-229, delivered by FEAT-055).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import ConfigParameter


class ConfigRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def values_for_profile(self, profile: str) -> dict[str, Any]:
        """All keys of one profile as `{key: JSON value}`."""
        rows = self.session.scalars(
            select(ConfigParameter).where(ConfigParameter.profile == profile)
        ).all()
        return {row.key: row.value for row in rows}

    def counts_by_profile(self) -> dict[str, int]:
        rows = self.session.execute(
            select(ConfigParameter.profile, func.count()).group_by(ConfigParameter.profile)
        ).all()
        return {profile: count for profile, count in rows}

    def get(self, profile: str, key: str) -> ConfigParameter | None:
        return self.session.get(ConfigParameter, (profile, key))

    def update_value(
        self, profile: str, key: str, value: Any, updated_by: uuid.UUID | None = None
    ) -> ConfigParameter:
        row = self.get(profile, key)
        if row is None:
            raise KeyError(f"{profile}.{key}")
        row.value = value
        row.updated_by = updated_by
        self.session.flush()
        return row
