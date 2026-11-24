"""Stage 2 - Fuzzy AHP weights for Severity, Occurrence and Detectability.

Buckley's (1985) geometric mean method. This is the script from Appendix E
of the report, restructured into functions so it can be tested and reused.
It produces exactly the same numbers as the submitted version.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .fuzzy import SAATY_SCALE, TFN

CRITERIA = ("Severity", "Occurrence", "Detectability")

# Random index for n = 3 (Saaty).
RANDOM_INDEX_3 = 0.58

# Pairwise judgements used in the project.
DEFAULT_JUDGEMENTS = {
    ("S", "O"): "mod_strong",  # Severity moderately-to-strongly more important than Occurrence
    ("S", "D"): "strong",      # Severity strongly more important than Detectability
    ("O", "D"): "weak",        # Occurrence weakly more important than Detectability
}


@dataclass(frozen=True)
class AHPResult:
    fuzzy_weights: tuple[TFN, TFN, TFN]
    crisp_weights: tuple[float, float, float]
    lambda_max: float
    consistency_index: float
    consistency_ratio: float

    @property
    def is_consistent(self) -> bool:
        return self.consistency_ratio < 0.10


def pairwise_matrix(so: TFN, sd: TFN, od: TFN) -> list[list[TFN]]:
    one = TFN(1, 1, 1)
    return [
        [one, so, sd],
        [so.reciprocal(), one, od],
        [sd.reciprocal(), od.reciprocal(), one],
    ]


def buckley_weights(matrix: list[list[TFN]]) -> list[TFN]:
    """Fuzzy weight per row: geometric mean of the row, divided by the column sums.

    The lower bound is divided by the sum of upper bounds and vice versa,
    which is how fuzzy division works for positive TFNs.
    """
    n = len(matrix)
    geo = [
        TFN(*(float(np.prod([row[j][k] for j in range(n)])) ** (1 / n) for k in range(3)))
        for row in matrix
    ]
    sum_l = sum(g.l for g in geo)
    sum_m = sum(g.m for g in geo)
    sum_u = sum(g.u for g in geo)
    return [TFN(g.l / sum_u, g.m / sum_m, g.u / sum_l) for g in geo]


def consistency(matrix: list[list[TFN]], crisp_weights: np.ndarray) -> tuple[float, float, float]:
    """Saaty's consistency check on the defuzzified matrix. Returns (lambda_max, CI, CR)."""
    n = len(matrix)
    crisp = np.array([[cell.defuzzify() for cell in row] for row in matrix])
    lambda_max = float(np.mean(crisp @ crisp_weights / crisp_weights))
    ci = (lambda_max - n) / (n - 1)
    return lambda_max, ci, ci / RANDOM_INDEX_3


def run(judgements: dict[tuple[str, str], str] = DEFAULT_JUDGEMENTS) -> AHPResult:
    matrix = pairwise_matrix(
        SAATY_SCALE[judgements[("S", "O")]],
        SAATY_SCALE[judgements[("S", "D")]],
        SAATY_SCALE[judgements[("O", "D")]],
    )
    fuzzy = buckley_weights(matrix)
    crisp = np.array([w.defuzzify() for w in fuzzy])
    crisp = crisp / crisp.sum()
    lam, ci, cr = consistency(matrix, crisp)
    return AHPResult(
        fuzzy_weights=tuple(fuzzy),
        crisp_weights=tuple(float(x) for x in crisp),
        lambda_max=lam,
        consistency_index=ci,
        consistency_ratio=cr,
    )


def report(result: AHPResult) -> str:
    lines = [
        "Fuzzy AHP - Buckley (1985) geometric mean",
        f"{'Criterion':<15}{'Fuzzy weight (l, m, u)':<30}Crisp",
    ]
    for name, fw, cw in zip(CRITERIA, result.fuzzy_weights, result.crisp_weights):
        lines.append(f"{name:<15}({fw.l:.4f}, {fw.m:.4f}, {fw.u:.4f})      {cw:.4f}")
    status = "OK" if result.is_consistent else "NOT consistent"
    lines.append(
        f"lambda_max = {result.lambda_max:.4f}   CI = {result.consistency_index:.4f}   "
        f"CR = {result.consistency_ratio:.4f} ({status}, threshold 0.10)"
    )
    return "\n".join(lines)
