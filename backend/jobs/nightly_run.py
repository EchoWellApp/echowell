"""Nightly pipeline entry point: `python -m backend.jobs.nightly_run` (TRD 15 DEP-047, TRD 24 D-47).

Runs the same startup guards as the web app (ENV-010). The run itself (facility-local hour check,
once-per-night dedupe, full pipeline run) is delivered by FEAT-054.
"""

from __future__ import annotations

import logging

from backend.core.config import load_settings_or_exit

logger = logging.getLogger("backend.jobs.nightly_run")


def main() -> int:
    load_settings_or_exit()
    logger.warning("nightly_run_not_available: the nightly run is delivered by FEAT-054")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
