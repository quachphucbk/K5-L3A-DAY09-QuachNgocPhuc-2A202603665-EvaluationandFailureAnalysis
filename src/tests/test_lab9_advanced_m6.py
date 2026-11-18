"""M6 estimator invariants and validation beyond public examples."""
import itertools
from math import comb
import pytest
from lab9.stats import pass_at_k, pass_hat_k
pytestmark = pytest.mark.student


def test_estimators_match_exhaustive_sampling():
    for n in range(1, 8):
        for c in range(n + 1):
            for k in range(1, n + 1):
                subsets = list(itertools.combinations(range(n), k))
                any_pass = sum(any(i < c for i in s) for s in subsets) / comb(n, k)
                all_pass = sum(all(i < c for i in s) for s in subsets) / comb(n, k)
                assert pass_at_k(n, c, k) == pytest.approx(any_pass)
                assert pass_hat_k(n, c, k) == pytest.approx(all_pass)
                assert pass_hat_k(n, c, k) <= c / n + 1e-12
                assert c / n <= pass_at_k(n, c, k) + 1e-12


@pytest.mark.parametrize("args", [(0, 0, 1), (-1, 0, 1), (5, -1, 1), (5, 6, 1),
                                  (5, 2, 0), (5, 2, 6), (5.0, 2, 1), (5, 2.5, 1),
                                  (5, 2, True), (True, 0, 1), (5, 2, None)])
def test_both_estimators_reject_invalid_arguments(args):
    for estimator in (pass_at_k, pass_hat_k):
        with pytest.raises(ValueError):
            estimator(*args)
