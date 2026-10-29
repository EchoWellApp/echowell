"""Ingest batches and rejections (TRD 23 §4.2.7, §4.2.8; TRD 06 DB-005; FEAT-010).

Records that fail validation are written only to `ingest_rejections` (DB-005). Rejections are
append-only for the application (SELECT, INSERT): this class has no update or delete for them.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import IngestBatch, IngestRejection, IngestSource
from backend.schemas.json_columns import ingest_errors_json


class IngestRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_batch(
        self,
        *,
        source: IngestSource,
        record_count: int = 0,
        filename: str | None = None,
        uploaded_by: uuid.UUID | None = None,
        api_key_id: uuid.UUID | None = None,
    ) -> IngestBatch:
        batch = IngestBatch(
            source=source,
            record_count=record_count,
            filename=filename,
            uploaded_by=uploaded_by,
            api_key_id=api_key_id,
        )
        self.session.add(batch)
        self.session.flush()
        return batch

    def update_counts(
        self, batch: IngestBatch, *, record: int, accepted: int, rejected: int, duplicates: int
    ) -> IngestBatch:
        """Set the batch counts once the batch is processed (`ingest_batches_counts_ck`)."""
        batch.record_count = record
        batch.accepted_count = accepted
        batch.rejected_count = rejected
        batch.duplicate_count = duplicates
        self.session.flush()
        return batch

    def link_run(self, batch: IngestBatch, pipeline_run_id: uuid.UUID) -> IngestBatch:
        """Record the run the batch started (TRD 20 §4.13, D-124)."""
        batch.pipeline_run_id = pipeline_run_id
        self.session.flush()
        return batch

    def get_batch(self, batch_id: uuid.UUID) -> IngestBatch | None:
        return self.session.get(IngestBatch, batch_id)

    def insert_rejection(
        self,
        *,
        raw_body: Any,
        errors: list[dict[str, str]],
        ingest_batch_id: uuid.UUID | None = None,
        api_key_id: uuid.UUID | None = None,
        row_number: int | None = None,
    ) -> IngestRejection:
        """Store one rejected record with its `{field, code, message}` errors (TRD 23 §4.5)."""
        rejection = IngestRejection(
            raw_body=raw_body,
            errors=ingest_errors_json(errors),
            ingest_batch_id=ingest_batch_id,
            api_key_id=api_key_id,
            row_number=row_number,
        )
        self.session.add(rejection)
        self.session.flush()
        return rejection

    def rejections_for_batch(self, batch_id: uuid.UUID) -> list[IngestRejection]:
        return list(
            self.session.scalars(
                select(IngestRejection)
                .where(IngestRejection.ingest_batch_id == batch_id)
                .order_by(IngestRejection.row_number, IngestRejection.received_at)
            ).all()
        )
