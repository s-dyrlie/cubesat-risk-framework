"""Stage 3 - Fuzzy TOPSIS ranking of failure modes (Chen, 2000).

Higher Severity, Occurrence and Detectability ratings all mean higher risk.
Each failure mode is therefore compared with two reference points:

* the most critical possible failure mode, (1, 1, 1) on every criterion
* the least critical possible failure mode, (0, 0, 0) on every criterion

Both references are weighted in the same way as the failure modes.

The closeness coefficient is

    CC = d_least / (d_most + d_least)

so CC is close to 1 for failure modes near the most critical reference.
Failure modes are ranked by descending CC: rank 1 is the highest priority.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .fuzzy import DETECTABILITY_SCALE, SEVERITY_OCCURRENCE_SCALE, TFN, vertex_distance

MOST_CRITICAL = TFN(1.0, 1.0, 1.0)
LEAST_CRITICAL = TFN(0.0, 0.0, 0.0)

PHASES = ("Pre-launch", "LEOP", "Commissioning", "Nominal Operations", "End-of-Life")

SCENARIOS: dict[str, tuple[float, float, float]] = {
    # Fuzzy AHP output (see fuzzy_ahp.py); filled in at runtime for "baseline".
    "equal": (1 / 3, 1 / 3, 1 / 3),
    "severity-reduced": (0.45, 0.35, 0.20),
}


@dataclass(frozen=True)
class FailureMode:
    id: str
    failure_mode: str
    subsystem: str
    phases: tuple[str, ...]
    severity: str
    occurrence: str
    detectability: str

    def tfns(self) -> tuple[TFN, TFN, TFN]:
        return (
            SEVERITY_OCCURRENCE_SCALE[self.severity],
            SEVERITY_OCCURRENCE_SCALE[self.occurrence],
            DETECTABILITY_SCALE[self.detectability],
        )

    def in_phase(self, phase: str) -> bool:
        """'All phases' failure modes are included in every phase."""
        return phase in self.phases or "All phases" in self.phases


@dataclass(frozen=True)
class RankedFailureMode:
    rank: int
    cc: float
    d_most: float
    d_least: float
    failure_mode: FailureMode


def load_register(path: str | Path) -> list[FailureMode]:
    modes = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            fm = FailureMode(
                id=row["id"],
                failure_mode=row["failure_mode"],
                subsystem=row["subsystem"],
                phases=tuple(row["phase"].split(";")),
                severity=row["severity"],
                occurrence=row["occurrence"],
                detectability=row["detectability"],
            )
            fm.tfns()  # fail early on an unknown or missing rating
            modes.append(fm)
    return modes


def rank(modes: list[FailureMode], weights: tuple[float, float, float]) -> list[RankedFailureMode]:
    if not modes:
        return []
    if abs(sum(weights) - 1) > 1e-6:
        raise ValueError(f"weights must sum to 1, got {sum(weights)}")

    matrix = [fm.tfns() for fm in modes]

    # Linear normalisation per criterion: divide by the largest upper bound,
    # so every value stays in [0, 1] and every TFN keeps l <= m <= u.
    max_u = [max(row[c].u for row in matrix) for c in range(3)]

    scored = []
    for fm, row in zip(modes, matrix):
        weighted = [row[c].scale(weights[c] / max_u[c]) for c in range(3)]
        # References are weighted the same way as the data, so a failure mode
        # rated (1, 1, 1) on every criterion gets CC = 1 and (0, 0, 0) gets CC = 0.
        d_most = sum(vertex_distance(weighted[c], MOST_CRITICAL.scale(weights[c])) for c in range(3))
        d_least = sum(vertex_distance(weighted[c], LEAST_CRITICAL) for c in range(3))
        scored.append((d_least / (d_most + d_least), d_most, d_least, fm))

    scored.sort(key=lambda s: (-round(s[0], 10), s[3].id))

    # Equal CC values share a rank (1, 2, 2, 4 ...), as in the report.
    ranked, prev_cc, prev_rank = [], None, 0
    for position, (cc, d_most, d_least, fm) in enumerate(scored, start=1):
        current_rank = prev_rank if prev_cc is not None and round(cc, 10) == round(prev_cc, 10) else position
        ranked.append(RankedFailureMode(current_rank, cc, d_most, d_least, fm))
        prev_cc, prev_rank = cc, current_rank
    return ranked
