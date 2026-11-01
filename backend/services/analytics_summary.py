"""The study-team summary `GET /api/v1/analytics` (TRD 05 API-087, API-136; TRD 09 CUS-047,
CUS-049; TRD 23 §4.7; FEAT-035).

This is the only module that reads `evaluation_ground_truth`, and only under profile `test_v0_1`,
through a second engine on DATABASE_READONLY_URL (login role `echowell_readonly`, `pool_size=1`,
read-only transactions, no `SET ROLE`). The pipeline never reads the answer key (TST-068). Under
profile `production` that engine is never created and `review_outcomes` replaces `alarm_timing`.

The `kpis`, `daily_series`, `funnel` and `by_resident` blocks are the engine's
`build_analytics_summary` on the stored rows of the latest runs (FEAT-051, TRD 24 D-79).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.aggregates import build_analytics_summary
from backend.core import db
from backend.core.config import Settings
from backend.models import EvaluationGroundTruth
from backend.repositories import read_models as rm
from backend.repositories.pipeline_run_repository import PipelineRunRepository
from backend.repositories.resident_repository import ResidentRepository
from backend.services import engine_read
from backend.services.pipeline_service import run_dto
from backend.services.resident_service import ReadContext, natural_key

logger = logging.getLogger("backend.analytics")

GroundTruthSessions = Callable[[], Session]
NOT_FORMED_NOTE = "Too few usable sessions: baseline pending, nothing scored"


def ground_truth_sessions(settings: Settings) -> GroundTruthSessions | None:
    """Sessions on the read-only engine under `test_v0_1`; None otherwise (API-136)."""
    if settings.pipeline_profile != "test_v0_1":
        return None
    if settings.database_readonly_url is None:
        logger.warning("alarm_timing_unavailable", extra={"reason": "no read-only URL"})
        return None
    engine = db.create_read_only_engine(settings.database_readonly_url, app_env=settings.app_env)
    return db.session_factory(engine)


def alarm_timing(session: Session, sessions: GroundTruthSessions) -> list[dict[str, Any]]:
    """One row per resident of the answer key (CUS-047, D-81)."""
    with sessions() as readonly:
        truth = readonly.execute(
            select(
                EvaluationGroundTruth.resident_code,
                EvaluationGroundTruth.planted_change,
                EvaluationGroundTruth.true_onset_date,
            )
        ).all()
    first = rm.first_alarm_dates(session)
    rows = []
    for code, planted, onset in sorted(truth, key=lambda t: natural_key(t[0])):
        rang = first.get(code)
        rows.append(
            {
                "resident_code": code, "planted_change": planted, "change_began": onset,
                "alarm_rang": rang, **_timing(onset, rang),
            }
        )  # fmt: skip
    return rows


def _timing(onset: date | None, rang: date | None) -> dict[str, Any]:
    """`detected` = alarm on or after the onset; an alarm before it is a false alarm (D-81)."""
    if onset is None:
        return {"delay_days": None, "result": "false_alarm" if rang else "correct_no_alarm"}
    if rang is None:
        return {"delay_days": None, "result": "missed"}
    if rang < onset:
        return {"delay_days": None, "result": "false_alarm"}
    return {"delay_days": (rang - onset).days, "result": "detected"}


def aggregate_blocks(session: Session, ctx: ReadContext, start: date, end: date) -> dict[str, Any]:
    """`kpis`, `daily_series`, `funnel`, `by_resident` from `build_analytics_summary` on the
    stored rows (FEAT-051, D-79), mapped to the TRD 19 E-18 names (FEAT-051-FR-12)."""
    stored = engine_read.stored_result(session, (start, end))
    as_of = ctx.meta.as_of or datetime.combine(end, time(12), tzinfo=ctx.tz)
    summary = build_analytics_summary(stored.sessions, stored.ledger, stored.epochs, stored.alerts,
                                      stored.data_alerts, stored.residents, ctx.pipeline_config,
                                      as_of)  # fmt: skip
    k = summary.kpis
    alarms = k["alarms_raised"]
    not_reviewed = rm.open_alerts_in(session, start, end) if alarms["value"] else 0
    funnel = {step["step"]: step for step in summary.funnel}
    return {
        "kpis": {
            "checkins_received": _count(k["checkins_received"]),
            "used_for_scoring": _count(k["used_for_scoring"]),
            "baselines_formed": {
                "formed": k["baselines_formed"]["value"],
                "residents": k["baselines_formed"]["total"],
                "forming_resident_codes": k["baselines_formed"]["forming"],
                "restarts": [{"resident_code": c, "restart_count": n}
                             for c, n in k["baselines_formed"]["restarts"].items()],
            },
            "alarms_raised": {"count": alarms["value"], "resident_codes": alarms["residents"],
                              "not_reviewed_count": not_reviewed},
        },
        "daily_series": list(summary.daily_series),
        "funnel": {
            "expected": funnel["expected"]["value"], "residents": funnel["expected"]["residents"],
            "days": funnel["expected"]["days"], "received": funnel["received"]["value"],
            "missed": funnel["received"]["missed"],
            "duplicates_removed": funnel["received"]["duplicates_removed"],
            "passed_quality": funnel["passed_quality"]["value"],
            "set_aside": funnel["passed_quality"]["set_aside"],
            "set_aside_reasons": funnel["passed_quality"]["set_aside_reasons"],
            "set_aside_multi_reason": funnel["passed_quality"]["set_aside_multi_reason"],
            "quarantined": funnel["used"]["quarantined"], "used": funnel["used"]["value"],
        },
        "by_resident": [{**row, "used_percent": row["used_percent"] or 0}
                        for row in summary.by_resident],
    }  # fmt: skip


def _count(block: dict[str, Any]) -> dict[str, int]:
    return {"count": block["value"], "expected": block["expected"],
            "percent": block["percent"] or 0}  # fmt: skip


def _alarm_timing_block(
    session: Session, test_profile: bool, ground_truth: GroundTruthSessions | None
) -> list[dict[str, Any]] | None:
    if not test_profile:
        return None
    return alarm_timing(session, ground_truth) if ground_truth is not None else []


def build(
    session: Session,
    ctx: ReadContext,
    settings: Settings,
    ground_truth: GroundTruthSessions | None,
) -> dict[str, Any]:
    """The complete `AnalyticsResponse` (TRD 19 E-18)."""
    start = ctx.as_of_date - timedelta(days=rm.WINDOW_DAYS - 1)
    residents = sorted(
        ResidentRepository(session).list_all(), key=lambda r: natural_key(r.resident_code)
    )
    counts = rm.status_counts(session, residents, ctx.as_of_date)
    totals = {key: sum(counts[r.id][key] for r in residents) for key in rm.STATUS_KEYS}
    status_counts = [{"resident_code": r.resident_code, **counts[r.id]} for r in residents]
    outcomes = sorted(
        rm.epoch_outcomes(session), key=lambda o: (natural_key(o.resident_code), o.epoch_number)
    )
    latest = PipelineRunRepository(session).latest_succeeded()
    test_profile = settings.pipeline_profile == "test_v0_1"
    review_outcomes = None
    if not test_profile:
        review_outcomes = asdict(rm.review_outcome_counts(session, start, ctx.as_of_date))
    return {
        "meta": ctx.meta,
        "period": {"from": start, "to": ctx.as_of_date, "days": rm.WINDOW_DAYS},
        **aggregate_blocks(session, ctx, start, ctx.as_of_date),
        "alarm_timing": (
            alarm_timing(session, ground_truth)
            if test_profile and ground_truth
            else []
            if test_profile
            else None
        ),
        "review_outcomes": review_outcomes,
        "status_totals": totals,
        "status_counts": status_counts,
        "resident_outcomes": [
            {
                **asdict(o),
                "scored_sessions": o.scored_sessions if o.baseline_formed else None,
                "note": None if o.baseline_formed else NOT_FORMED_NOTE,
            }
            for o in outcomes
        ],
        "pipeline_run": run_dto(latest) if latest is not None else None,
    }
