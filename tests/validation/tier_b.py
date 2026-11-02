"""Tier B results in the answer-key shape (TRD 14 TDV-031, §4.5; FEAT-058-FR-03).

`collect` reads a `tests.support.system.TierB` run back through the API (analytics, baselines,
scores, data alerts) and read-only SELECTs (processed sessions, ledger, epochs, alerts, cusum
state) into `Outputs`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from analytics import COMPOSITE_KEYS
from tests.support.system import TierB
from tests.validation.outputs import (
    NO_RECORD,
    Outputs,
    alert_row,
    annotated_row,
    day_of,
    feature_label,
    offsets_of,
    outcome_row,
    params_of,
    record_values,
    score_row,
)


def collect(harness: TierB) -> Outputs:
    out = Outputs()
    snapshot = harness.select(  # the run DTO has no snapshot; the run row does (VC-G08)
        "SELECT config_snapshot FROM pipeline_runs WHERE id = :id", id=harness.run["id"]
    )[0][0]
    baseline_n = int(snapshot["baseline_n"])
    sessions = harness.select(
        "SELECT p.status, p.reason_text, p.local_date, p.local_time, p.is_morning, "
        "p.baseline_ordinal, p.in_baseline, p.adjusted_features, p.session_id, e.epoch_number, "
        "r.arrival_seq, r.payload, "
        "res.resident_code "
        "FROM processed_sessions p JOIN raw_sessions r ON r.id = p.raw_session_id "
        "JOIN residents res ON res.id = p.resident_id "
        "LEFT JOIN epochs e ON e.id = p.epoch_id ORDER BY r.arrival_seq")  # fmt: skip
    first_seq = min(s.arrival_seq for s in sessions)
    for s in sessions:
        key = (s.resident_code, day_of(s.local_date), s.arrival_seq - first_seq + 1)
        out.annotated[key] = annotated_row(
            local_time=f"{s.local_date.isoformat()} {s.local_time.strftime('%H:%M')}",
            status=s.status, reason=s.reason_text, morning=s.is_morning, epoch=s.epoch_number,
            ordinal=s.baseline_ordinal, in_baseline=s.in_baseline,
            record=record_values(payload_row(s.payload)), baseline_n=baseline_n,
        )  # fmt: skip
        if s.status != "duplicate":
            out.adjusted[(s.session_id,)] = {k: float(s.adjusted_features[k])
                                             for k in COMPOSITE_KEYS}  # fmt: skip
    ledger = harness.select(
        "SELECT res.resident_code, d.local_date, d.status, dev.device_code, d.reason "
        "FROM day_ledger d JOIN residents res ON res.id = d.resident_id "
        "LEFT JOIN devices dev ON dev.id = d.device_id")  # fmt: skip
    for d in ledger:
        out.ledger.append((d.resident_code, d.local_date, d.status, d.device_code, d.reason))
        if d.status != "checked_in":
            out.annotated[(d.resident_code, day_of(d.local_date), NO_RECORD)] = annotated_row(
                local_time=d.local_date.isoformat(), status=d.status, reason=d.reason,
                morning=None, epoch=None, ordinal=None, in_baseline=False,
                record=record_values(None, device=d.device_code), baseline_n=baseline_n,
            )  # fmt: skip
    out.ledger.sort()
    analytics = harness.get("/analytics", role="researcher")
    for row in analytics["status_counts"]:
        out.status_counts[(row["resident_code"],)] = {
            k: v for k, v in row.items() if k != "resident_code"}  # fmt: skip
    for row in analytics["resident_outcomes"]:
        out.outcomes[(row["resident_code"], row["epoch_number"])] = outcome_row(
            device=row["device_code"], usable=row["usable_in_epoch"],
            formed=row["baseline_formed"], frozen_after=row["baseline_frozen_after"],
            scored=row["scored_sessions"] or 0, first_alarm=row["first_alarm_session"],
        )  # fmt: skip
    for b in harness.items("/analytics/baselines"):
        out.baselines[(b["resident_code"], b["epoch_number"], feature_label(b["feature_key"]))] = {
            "device_id": b["device_code"], "n_sessions": b["n_sessions"],
            "first_session": b["first_session_id"],
            "baseline_frozen_after": b["frozen_after_session_id"], "median": b["median"],
            "mad": b["mad"], "robust_spread": b["robust_spread"],
            "floor_applied": b["floor_applied"],
        }  # fmt: skip
    for code in sorted({k[0] for k in out.status_counts}):
        for s in harness.items("/scores", resident_code=code):
            out.scores[(s["session_id"],)] = score_row(
                resident=s["resident_code"], epoch=s["epoch_number"],
                local=date.fromisoformat(s["local_date"]), morning=s["is_morning"], z=s["z"],
                composite_raw=s["composite_raw"], composite_z=s["composite_z"],
                tally=s["cusum_tally"], alarm=s["alarm_state"],
            )  # fmt: skip
    out.params = params_of(snapshot)
    out.morning_offsets = offsets_of(snapshot)
    for a in harness.select(
        "SELECT res.resident_code, e.epoch_number, a.session_id, a.triggered_at, a.local_date, "
        "a.cusum_value, a.status FROM alerts a JOIN epochs e ON e.id = a.epoch_id "
        "JOIN residents res ON res.id = a.resident_id"
    ):  # fmt: skip
        out.alerts.append(alert_row(
            resident=a.resident_code, epoch=a.epoch_number, session=a.session_id,
            triggered=a.triggered_at, local=a.local_date, value=a.cusum_value,
            status="closed" if a.status == "closed" else "open",
        ))  # fmt: skip
    out.alerts.sort(key=lambda a: (a["resident_id"], a["epoch"]))
    for c in harness.select(
        "SELECT res.resident_code, e.epoch_number, c.current_tally, c.alarm_on "
        "FROM cusum_state c JOIN epochs e ON e.id = c.epoch_id "
        "JOIN residents res ON res.id = c.resident_id"
    ):  # fmt: skip
        out.cusum[(c.resident_code, c.epoch_number)] = {
            "current_tally": c.current_tally, "alarm_on": c.alarm_on}  # fmt: skip
    out.data_alerts = sorted(
        (a["kind"], a["resident_code"] or a["device_code"] or "", a["title"], a["detail"])
        for a in harness.items("/data-alerts", status="open")
    )  # fmt: skip
    return out


def payload_row(payload: dict[str, Any]) -> dict[str, str]:
    """A stored payload as the CSV row it came from (values as received, TRD 14 VC-G11)."""
    row = {k: ("" if v is None else str(v)) for k, v in payload.items()}
    if "resident_code" in row and "resident_id" not in row:
        row["resident_id"] = row["resident_code"]
    return row
