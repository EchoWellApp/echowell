"""CSV exports of the read-out endpoints (TRD 05 API-129; TRD 13 TST-079; FEAT-034).

A CSV holds the TRD 19 DTO field names as its header (nested `z` flattened to `z_<feature>`), every
row matching the filters, and values written as in JSON: floats at full precision (`str(float)`),
booleans `true`/`false`, dates ISO 8601, null as an empty cell. Each export writes one
`export.csv` audit row. More than 100,000 rows is refused with 413 before anything is sent.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Iterator, Sequence
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.core.errors import PayloadTooLargeError
from backend.models import ActorType
from backend.services import audit_service
from backend.services.audit_service import AuditAction

MAX_CSV_ROWS = 100_000
CSV_MEDIA_TYPE = "text/csv; charset=utf-8"


def wants_csv(accept: str | None) -> bool:
    """Content negotiation on `Accept: text/csv` (API-129)."""
    return any(
        part.split(";")[0].strip().lower() == "text/csv" for part in (accept or "").split(",")
    )


def check_size(row_count: int) -> None:
    if row_count > MAX_CSV_ROWS:
        raise PayloadTooLargeError(
            f"The export has {row_count} rows; at most {MAX_CSV_ROWS} can be exported. Narrow the "
            "filters."
        )


def cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


def lines(header: Sequence[str], rows: Iterable[Sequence[Any]]) -> Iterator[str]:
    """The CSV text in chunks, header first (RFC 4180, CRLF line ends)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for row in rows:
        writer.writerow([cell(v) for v in row])
        if buffer.tell() > 64_000:
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate()
    yield buffer.getvalue()


def filename(kind: str, as_of_date: date) -> str:
    return f"echowell_{kind}_{as_of_date.isoformat()}.csv"


def audit_export(
    session: Session, *, route: str, filters: dict[str, Any], row_count: int, actor_id: str
) -> None:
    """One `export.csv` row: entity route / route template, details `{filters, row_count}`."""
    audit_service.record(
        session, action=AuditAction.EXPORT_CSV, actor_type=ActorType.USER, actor_id=actor_id,
        entity_type="route", entity_id=route,
        details={"filters": {k: cell(v) for k, v in filters.items() if v is not None},
                 "row_count": row_count},
    )  # fmt: skip
