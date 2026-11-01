"""Alarm events and "Leaning most" (TRD 09 §4.2, §4.8; FEAT-048)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from analytics.alert_generator import generate_alerts, leaning_most
from analytics.config import LEANING_LABELS, TEST_V0_1, ContractError, EpochSummary, ScoreRow
from tests.unit.analytics.src05 import result

pytestmark = pytest.mark.unit


def _row(i: int, state: str, epoch: int = 1, **z: float) -> ScoreRow:
    zs = {f"z_{k}": z.get(k, 0.0) for k in LEANING_LABELS}
    return ScoreRow(f"S{i}", f"r{i}", "R01", epoch, date(2026, 10, i), False, zs, 0.0, 0.0,
                    cusum_tally=float(i), alarm_state=state)  # type: ignore[arg-type]  # fmt: skip


def _epoch(n: int, ended: datetime | None) -> EpochSummary:
    start = datetime(2026, 10, 1, tzinfo=UTC)
    return EpochSummary("R01", n, "D01", "fw", "sw", start, ended, 16, True, "S0", 3, None, 0.0,
                        None, False, None)  # fmt: skip


@pytest.mark.req("CUS-011", "CUS-012", "CUS-013", "AL-01", "AL-02", "FEAT-048-AC-01",
                 "FEAT-048-FR-01", "FEAT-048-FR-02", "FEAT-048-FR-03")  # fmt: skip
def test_one_event_per_ringing_epoch_with_closure_facts() -> None:
    stamp = datetime(2026, 10, 2, 19, tzinfo=UTC)
    ended = datetime(2026, 10, 20, tzinfo=UTC)
    rows = [_row(1, "off"), _row(2, "rings"), _row(3, "on"), _row(4, "off", epoch=2)]
    events = generate_alerts(rows, [_epoch(1, ended), _epoch(2, None)], TEST_V0_1,
                             timestamps={"S2": stamp})  # fmt: skip
    assert len(events) == 1
    e = events[0]
    assert (e.session_id, e.triggered_at, e.cusum_value, e.epoch_ended, e.epoch_ended_at) == (
        "S2", stamp, 2.0, True, ended
    )  # fmt: skip
    with pytest.raises(ContractError):
        generate_alerts(rows, [], TEST_V0_1)


@pytest.mark.req("CUS-041", "FEAT-048-FR-06", "FEAT-048-AC-02")
def test_leaning_most_rules() -> None:
    alert = generate_alerts([_row(2, "rings")], [], TEST_V0_1,
                            timestamps={"S2": datetime(2026, 10, 2, tzinfo=UTC)})[0]  # fmt: skip
    rows = [
        _row(1, "off", loudness_dbfs=-50.0),  # before the alert: ignored
        _row(2, "rings", loudness_dbfs=-2.0, pause_fraction=1.0, voiced_fraction=-1.0),
        _row(3, "on", loudness_dbfs=-2.0, pause_fraction=1.0, voiced_fraction=-1.0,
             number_of_pauses=0.5, speech_rate_syl_per_s=1.0),
    ]  # fmt: skip
    # signed means: loudness 2.0, pause_fraction 1.0, voiced 1.0, pauses 0.25, speech rate -1.0
    assert leaning_most(rows, alert, TEST_V0_1) == (
        "loudness_dbfs", "pause_fraction", "voiced_fraction"
    )  # fmt: skip
    flat = [_row(2, "rings", total_phrase_duration_s=-1.0)]
    assert leaning_most(flat, alert, TEST_V0_1) == ()


@pytest.mark.req("CUS-041", "VC-R09", "VC-R10", "FEAT-048-AC-03")
def test_src05_alerts_and_leaning_most() -> None:
    alerts = {a.resident_code: a for a in result().alerts}
    assert sorted(alerts) == ["R09", "R10"]
    labels = {code: ", ".join(LEANING_LABELS[k] for k in a.leaning_most)
              for code, a in alerts.items()}  # fmt: skip
    assert labels == {
        "R09": "more pauses, quieter, less voiced sound",
        "R10": "more pauses, slower while talking, fewer syllables per second",
    }
    assert (alerts["R09"].local_date, alerts["R10"].local_date) == (
        date(2026, 10, 21),
        date(2026, 10, 24),
    )
    assert not any(a.epoch_ended for a in alerts.values())
