"""Triangular fuzzy numbers (TFNs) and the linguistic scales used by CSRM."""

from __future__ import annotations

import math
from typing import NamedTuple


class TFN(NamedTuple):
    """A triangular fuzzy number (l, m, u) with l <= m <= u."""

    l: float
    m: float
    u: float

    def is_valid(self) -> bool:
        return self.l <= self.m <= self.u

    def reciprocal(self) -> "TFN":
        """Reciprocal of (l, m, u) is (1/u, 1/m, 1/l)."""
        return TFN(1 / self.u, 1 / self.m, 1 / self.l)

    def scale(self, k: float) -> "TFN":
        return TFN(self.l * k, self.m * k, self.u * k)

    def defuzzify(self) -> float:
        """Centroid (graded mean) of the triangle."""
        return (self.l + self.m + self.u) / 3


def vertex_distance(a: TFN, b: TFN) -> float:
    """Vertex distance between two TFNs (Chen, 2000)."""
    return math.sqrt(((a.l - b.l) ** 2 + (a.m - b.m) ** 2 + (a.u - b.u) ** 2) / 3)


# Fuzzy Saaty scale for pairwise comparisons (report, Table 7).
SAATY_SCALE: dict[str, TFN] = {
    "equal": TFN(1, 1, 1),
    "weak": TFN(1, 2, 3),
    "moderate": TFN(2, 3, 4),
    "mod_strong": TFN(3, 4, 5),
    "strong": TFN(4, 5, 6),
    "strong_very": TFN(5, 6, 7),
    "very_strong": TFN(6, 7, 8),
    "very_extreme": TFN(7, 8, 9),
    "extreme": TFN(8, 9, 9),
}

# Linguistic ratings for Severity and Occurrence -> TFN on [0, 1].
# These are the values the project's FTOPSIS sheet used.
SEVERITY_OCCURRENCE_SCALE: dict[str, TFN] = {
    "Very Low": TFN(0.0, 0.1, 0.3),
    "Low": TFN(0.1, 0.3, 0.5),
    "Moderate": TFN(0.3, 0.5, 0.7),
    "High": TFN(0.5, 0.7, 0.9),
    "Very High": TFN(0.7, 0.9, 1.0),
}

# Detectability: the harder a failure is to detect, the higher the risk.
DETECTABILITY_SCALE: dict[str, TFN] = {
    "Very Easy": TFN(0.0, 0.1, 0.3),
    "Easy": TFN(0.1, 0.3, 0.5),
    "Moderate": TFN(0.3, 0.5, 0.7),
    "Difficult": TFN(0.5, 0.7, 0.9),
    "Very Difficult": TFN(0.7, 0.9, 1.0),
}
