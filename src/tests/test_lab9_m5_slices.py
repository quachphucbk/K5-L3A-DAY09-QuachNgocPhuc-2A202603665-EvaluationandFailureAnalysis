"""M5 slice regressions: decisions depend on rows, not variant names."""
import copy
import pytest
pytestmark = pytest.mark.student


def report(value):
    return {"rows": [{"item_id": f"E-{i}", "seed": s, "pass_rate": value,
                      "slices": ["money_movement"]} for i in range(3) for s in (11, 22)]}


def test_slice_significant_drop_without_floor():
    from lab9.gate import slice_check
    spec = {"slices": [{"name": "money_movement", "metric": "pass_rate",
                         "no_significant_drop": True, "blocking": True}]}
    blocked, _ = slice_check(report(False), report(True), spec)
    assert blocked == ["slice:money_movement/pass_rate"]
    assert slice_check(report(True), report(True), spec)[0] == []


def test_slice_rejects_missing_items_and_respects_nonblocking():
    from lab9.gate import slice_check
    spec = {"slices": [{"name": "money_movement", "metric": "pass_rate", "blocking": True}]}
    base = report(True)
    pr = copy.deepcopy(base)
    pr["rows"] = [r for r in pr["rows"] if r["item_id"] != "E-0"]
    assert slice_check(pr, base, spec)[0] == ["slice:money_movement/pass_rate"]
    spec["slices"][0]["blocking"] = False
    assert slice_check(pr, base, spec)[0] == []
