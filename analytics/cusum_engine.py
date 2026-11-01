"""One-sided upper CUSUM per resident-epoch (TRD 09 §4.1 CUS-001..CUS-010; FEAT-047).

S_i = max(0, S_{i-1} + composite_z_i - k) over the scored sessions of an epoch in time order,
starting at 0; the first i with S_i >= h "rings" and every later session is "on" even if S drops
below h (CUS-007). A plain float loop, because the max(0, ·) makes the tally path dependent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from analytics.config import AlarmState, PipelineConfig, ScoreRow


def run_cusum(rows: Sequence[ScoreRow], config: PipelineConfig) -> list[ScoreRow]:
    """Rows must be in time order within each (resident, epoch); other groups may interleave."""
    state: dict[tuple[str, int], tuple[float, bool]] = {}
    out = []
    for row in rows:
        key = (row.resident_code, row.epoch_number)
        tally, rung = state.get(key, (0.0, False))
        tally = max(0.0, tally + row.composite_z - config.cusum_k)
        alarm: AlarmState
        if not rung and tally >= config.cusum_h:
            alarm, rung = "rings", True
        elif rung:
            alarm = "on"
        else:
            alarm = "off"
        state[key] = (tally, rung)
        out.append(replace(row, cusum_tally=tally, alarm_state=alarm))
    return out
