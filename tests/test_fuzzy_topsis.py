from pathlib import Path

import pytest

from csrm.fuzzy import DETECTABILITY_SCALE, SEVERITY_OCCURRENCE_SCALE
from csrm.fuzzy_topsis import FailureMode, load_register, rank

REGISTER = Path(__file__).resolve().parent.parent / "data" / "fmea_register.csv"
BASELINE = (0.6750, 0.2006, 0.1244)


def fm(id, s, o, d, phases=("LEOP",)):
    return FailureMode(id=id, failure_mode=id, subsystem="EPS", phases=phases,
                       severity=s, occurrence=o, detectability=d)


@pytest.fixture(scope="module")
def register():
    return load_register(REGISTER)


def test_register_is_complete(register):
    assert len(register) == 48
    assert len({m.id for m in register}) == 48


def test_every_rating_maps_to_a_valid_tfn(register):
    for m in register:
        assert all(t.is_valid() for t in m.tfns()), m.id


def test_scales_are_ordered():
    for scale in (SEVERITY_OCCURRENCE_SCALE, DETECTABILITY_SCALE):
        mids = [t.m for t in scale.values()]
        assert mids == sorted(mids)


def test_cc_is_between_zero_and_one(register):
    for r in rank(register, BASELINE):
        assert 0.0 <= r.cc <= 1.0


def test_reference_points_give_cc_0_and_1():
    worst = fm("worst", "Very High", "Very High", "Very Difficult")
    best = fm("best", "Very Low", "Very Low", "Very Easy")
    ranked = {r.failure_mode.id: r for r in rank([worst, best], BASELINE)}
    assert ranked["worst"].rank == 1
    assert ranked["worst"].cc > ranked["best"].cc


def test_higher_rating_never_lowers_priority():
    """The bug in the submitted spreadsheet: raising a rating must not lower the risk."""
    base = fm("base", "Moderate", "Moderate", "Moderate")
    for higher in (
        fm("S+", "High", "Moderate", "Moderate"),
        fm("O+", "Moderate", "High", "Moderate"),
        fm("D+", "Moderate", "Moderate", "Difficult"),
    ):
        ranked = {r.failure_mode.id: r.cc for r in rank([base, higher], BASELINE)}
        assert ranked[higher.id] > ranked["base"], higher.id


def test_severity_outweighs_occurrence_under_baseline():
    a = fm("high_S", "Very High", "Low", "Moderate")
    b = fm("high_O", "Low", "Very High", "Moderate")
    ranked = {r.failure_mode.id: r.cc for r in rank([a, b], BASELINE)}
    assert ranked["high_S"] > ranked["high_O"]


def test_ties_share_a_rank():
    ranked = rank([fm("a", "High", "High", "Easy"), fm("b", "High", "High", "Easy"),
                   fm("c", "Low", "Low", "Easy")], BASELINE)
    assert [r.rank for r in ranked] == [1, 1, 3]


def test_all_phases_modes_appear_in_every_phase():
    m = fm("x", "High", "High", "Easy", phases=("All phases",))
    assert m.in_phase("LEOP") and m.in_phase("End-of-Life")


def test_weights_must_sum_to_one(register):
    with pytest.raises(ValueError):
        rank(register, (0.5, 0.5, 0.5))


def test_unknown_rating_is_rejected():
    with pytest.raises(KeyError):
        fm("bad", "", "High", "Easy").tfns()
