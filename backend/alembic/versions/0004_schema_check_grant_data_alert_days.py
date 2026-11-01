"""Let the app role read the schema revision; store the days of a data alert.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-31

The SQL is TRD 20 §4.14 verbatim (TRD 24 D-129, D-130; checkpoint 5 review, GitHub PR #20 Q-1
and Q-3). `SELECT` on `alembic_version` lets the nightly job compare the applied revision with
the one bundled with the code before it runs (DEP-048). `data_alerts.days` holds the
facility-local days an alert is about (the silent days of `device_silent`, the dates of the
quarantined or set-aside check-ins; empty for `baseline_stalled` and review-flagged rows), so
readers use stored dates and the detail text is derived from them, never parsed.
"""

from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

UPGRADE = """
GRANT SELECT ON alembic_version TO echowell_app;
ALTER TABLE data_alerts ADD COLUMN days date[] NOT NULL DEFAULT '{}';
"""

DOWNGRADE = """
ALTER TABLE data_alerts DROP COLUMN days;
REVOKE SELECT ON alembic_version FROM echowell_app;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
