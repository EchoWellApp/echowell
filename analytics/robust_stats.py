"""Median, MAD and scaled spread with floor (TRD 08 §4.2 BSC-001..BSC-005; FEAT-040).

Medians use `numpy.median` on a float64 array, so an even count gives the mean of the two middle
values (BSC-001); `floor_applied` is true only when the floor strictly raises the spread (BSC-004).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from analytics.config import ContractError, RobustStats


def robust(values: Sequence[float], floor: float, mad_scale: float) -> RobustStats:
    a = np.asarray(values, dtype=np.float64)
    if a.size == 0:
        raise ContractError("robust(): no values")
    if not np.all(np.isfinite(a)):
        raise ContractError("robust(): non-finite value")
    median = float(np.median(a))
    mad = float(np.median(np.abs(a - median)))
    scaled = mad * mad_scale
    spread = max(scaled, floor)
    return RobustStats(median=median, mad=mad, spread=spread, floor_applied=spread > scaled)
