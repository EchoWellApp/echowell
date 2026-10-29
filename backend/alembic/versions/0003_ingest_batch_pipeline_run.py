"""Link an ingest batch to the pipeline run it started.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-29

The SQL is TRD 20 §4.13 verbatim (TRD 24 D-124; checkpoint 4 review, GitHub PR #18 Q-1).
`GET /api/v1/ingest/batches/{id}` reads the column; the `ingest.batch.received` audit row keeps
recording the same id for traceability.
"""

from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

UPGRADE = """
ALTER TABLE ingest_batches
  ADD COLUMN pipeline_run_id uuid NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT;
CREATE INDEX ingest_batches_pipeline_run_idx ON ingest_batches (pipeline_run_id);
"""

DOWNGRADE = """
DROP INDEX ingest_batches_pipeline_run_idx;
ALTER TABLE ingest_batches DROP COLUMN pipeline_run_id;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
