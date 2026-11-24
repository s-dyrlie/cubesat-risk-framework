"""Command line entry point: python -m csrm [options]"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from . import fuzzy_ahp
from .fuzzy_topsis import PHASES, SCENARIOS, load_register, rank

DEFAULT_REGISTER = Path(__file__).resolve().parent.parent / "data" / "fmea_register.csv"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m csrm",
        description="Rank CubeSat failure modes with Fuzzy AHP weights and Fuzzy TOPSIS.",
    )
    parser.add_argument("--register", type=Path, default=DEFAULT_REGISTER, help="FMEA register CSV")
    parser.add_argument("--phase", choices=PHASES, help="only rank failure modes in this mission phase")
    parser.add_argument(
        "--scenario",
        choices=["baseline", *SCENARIOS],
        default="baseline",
        help="weight scenario (baseline = Fuzzy AHP weights)",
    )
    parser.add_argument("--top", type=int, default=10, help="rows to print (0 = all)")
    parser.add_argument("--compare", action="store_true", help="compare ranks across all weight scenarios")
    parser.add_argument("--csv", type=Path, help="also write the full ranking to this CSV file")
    args = parser.parse_args(argv)

    ahp = fuzzy_ahp.run()
    print(fuzzy_ahp.report(ahp))
    print()

    scenarios = {"baseline": ahp.crisp_weights, **SCENARIOS}
    modes = load_register(args.register)
    if args.phase:
        modes = [fm for fm in modes if fm.in_phase(args.phase)]
    scope = f"phase: {args.phase}" if args.phase else "all phases"

    if args.compare:
        results = {name: {r.failure_mode.id: r for r in rank(modes, w)} for name, w in scenarios.items()}
        base = sorted(results["baseline"].values(), key=lambda r: (r.rank, r.failure_mode.id))
        limit = base if args.top == 0 else base[: args.top]
        print(f"Rank under each weight scenario ({len(modes)} failure modes, {scope})")
        print(f"{'ID':<7}{'Failure mode':<46}{'baseline':>9}{'equal':>7}{'sev-red':>9}")
        for r in limit:
            fid = r.failure_mode.id
            print(
                f"{fid:<7}{r.failure_mode.failure_mode[:44]:<46}{r.rank:>9}"
                f"{results['equal'][fid].rank:>7}{results['severity-reduced'][fid].rank:>9}"
            )
        return 0

    weights = scenarios[args.scenario]
    ranked = rank(modes, weights)
    print(
        f"Fuzzy TOPSIS ranking - {len(modes)} failure modes, {scope}, scenario: {args.scenario} "
        f"(S={weights[0]:.3f}, O={weights[1]:.3f}, D={weights[2]:.3f})"
    )
    print(f"{'Rank':>4}  {'ID':<6} {'CC':>6}  {'S / O / D':<34} Failure mode")
    for r in ranked if args.top == 0 else ranked[: args.top]:
        fm = r.failure_mode
        sod = f"{fm.severity} / {fm.occurrence} / {fm.detectability}"
        print(f"{r.rank:>4}  {fm.id:<6} {r.cc:.4f}  {sod:<34} {fm.failure_mode}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["rank", "id", "failure_mode", "subsystem", "phase",
                             "severity", "occurrence", "detectability", "d_most", "d_least", "cc"])
            for r in ranked:
                fm = r.failure_mode
                writer.writerow([r.rank, fm.id, fm.failure_mode, fm.subsystem, ";".join(fm.phases),
                                 fm.severity, fm.occurrence, fm.detectability,
                                 f"{r.d_most:.4f}", f"{r.d_least:.4f}", f"{r.cc:.4f}"])
        print(f"\nFull ranking written to {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
