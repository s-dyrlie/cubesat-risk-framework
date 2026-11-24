import pytest

from csrm import fuzzy_ahp


@pytest.fixture(scope="module")
def result():
    return fuzzy_ahp.run()


def test_crisp_weights_match_report(result):
    # Report, Table 8: S = 0.6750, O = 0.2006, D = 0.1244
    assert result.crisp_weights == pytest.approx((0.6750, 0.2006, 0.1244), abs=1e-4)


def test_fuzzy_weights_match_report(result):
    expected = [(0.4833, 0.6833, 0.9544), (0.1234, 0.1998, 0.3071), (0.0805, 0.1168, 0.1935)]
    for got, exp in zip(result.fuzzy_weights, expected):
        assert tuple(got) == pytest.approx(exp, abs=1e-4)


def test_consistency_ratio_matches_report_and_passes(result):
    assert result.consistency_ratio == pytest.approx(0.0948, abs=1e-4)
    assert result.is_consistent


def test_weights_sum_to_one_and_are_valid_tfns(result):
    assert sum(result.crisp_weights) == pytest.approx(1.0)
    assert all(w.is_valid() for w in result.fuzzy_weights)


def test_severity_dominates(result):
    s, o, d = result.crisp_weights
    assert s > o > d


def test_equal_judgements_give_equal_weights():
    res = fuzzy_ahp.run({("S", "O"): "equal", ("S", "D"): "equal", ("O", "D"): "equal"})
    assert res.crisp_weights == pytest.approx((1 / 3, 1 / 3, 1 / 3))
    assert res.consistency_ratio == pytest.approx(0.0, abs=1e-12)
