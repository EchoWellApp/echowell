"""The last-admin invariant of `user_service.update` (TRD 05 API-092; FEAT-037-AC-06).

Through HTTP the state is unreachable (the caller is itself an active admin and SEC-044 forbids
changing one's own role or active flag), so the guard is tested at service level.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from backend.core.errors import LastAdminError
from backend.models import UserRole
from backend.services import user_service

pytestmark = pytest.mark.unit


class FakeUsers:
    def __init__(self, session: Any) -> None:
        self.writes: list[Any] = []

    def get(self, user_id: uuid.UUID) -> Any:
        return ONLY_ADMIN if user_id == ONLY_ADMIN.id else None

    def active_admins_for_update(self) -> list[Any]:
        return [ONLY_ADMIN]

    def update(self, user: Any, **changes: Any) -> None:
        WRITES.append(changes)


ONLY_ADMIN = SimpleNamespace(id=uuid.uuid4(), role=UserRole.ADMIN, active=True, email="a@x.test")
ACTOR = SimpleNamespace(id=uuid.uuid4(), role=UserRole.CLINICIAN, active=True)
WRITES: list[Any] = []


@pytest.mark.req("API-092", "FEAT-037-AC-06", "FEAT-037-FR-07")
@pytest.mark.parametrize(
    "change", [{"active": False}, {"role": "researcher"}, {"role": "clinician"}]
)
def test_last_active_admin_cannot_be_removed(
    monkeypatch: pytest.MonkeyPatch, change: dict[str, Any]
) -> None:
    monkeypatch.setattr(user_service, "UserRepository", FakeUsers)
    WRITES.clear()
    with pytest.raises(LastAdminError):
        user_service.update(None, ACTOR, ONLY_ADMIN.id, change)  # type: ignore[arg-type]
    assert WRITES == []
