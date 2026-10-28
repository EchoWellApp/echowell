"""Request dependencies get_db and get_pagination (TRD 05 API-011, API-016, API-017; FEAT-003)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.api import deps
from backend.core.errors import InvalidQueryParameterError

pytestmark = pytest.mark.unit


@pytest.mark.req("API-016")
def test_pagination_defaults_and_bounds() -> None:
    assert deps.get_pagination() == deps.Pagination(limit=50, offset=0)
    assert deps.get_pagination(limit=500, offset=7) == deps.Pagination(limit=500, offset=7)
    for kwargs in ({"limit": 0}, {"limit": 501}, {"offset": -1}):
        with pytest.raises(InvalidQueryParameterError) as exc:
            deps.get_pagination(**kwargs)
        assert (exc.value.status_code, exc.value.code) == (422, "INVALID_QUERY_PARAMETER")


@pytest.mark.req("API-011")
def test_get_db_commits_on_success_and_closes() -> None:
    session = MagicMock()
    with patch.object(deps.db, "session_factory", return_value=MagicMock(return_value=session)):
        gen = deps.get_db(MagicMock())
        assert next(gen) is session
        with pytest.raises(StopIteration):
            next(gen)
    session.commit.assert_called_once()
    session.rollback.assert_not_called()
    session.close.assert_called_once()


@pytest.mark.req("API-011")
def test_get_db_rolls_back_on_exception_and_closes() -> None:
    session = MagicMock()
    with patch.object(deps.db, "session_factory", return_value=MagicMock(return_value=session)):
        gen = deps.get_db(MagicMock())
        next(gen)
        with pytest.raises(RuntimeError):
            gen.throw(RuntimeError("handler failed"))
    session.commit.assert_not_called()
    session.rollback.assert_called_once()
    session.close.assert_called_once()
