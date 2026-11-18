"""M3: replay faulty traces and honest controls on isolated temporary stores."""
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.student
ROOT = Path(__file__).resolve().parents[1]


def evaluate_trial(tmp_path, monkeypatch, bugs, claim, seed):
    from lab8.db import load_json, load_jsonl
    from lab8.shapes import SHAPES
    from lab9.eval import make_task
    from lab9.variant_agent import make_shape
    claims = load_jsonl(ROOT / "data/public_claims.jsonl")
    labels = {c["claim_id"]: c["expected"] for c in claims}
    world = load_json(ROOT / "data/public_world_state.json")
    name = "m3_" + "_".join(sorted(bugs))
    monkeypatch.setitem(SHAPES, name, make_shape(name, {"no_override", *bugs}))
    monkeypatch.chdir(tmp_path)
    trial = make_task(name, world, claims, labels, tmp_path)({"claim_id": claim, "seed": seed})
    return SimpleNamespace(output=trial, expected_output=labels[claim])


@pytest.mark.parametrize("seed", [11, 22, 33, 44, 55])
@pytest.mark.parametrize("bug,claim", [
    ("leaky_trace", "C-001"), ("ignore_denied", "C-007"),
    ("ticket_trust", "C-002"), ("sum_parts", "C-014"),
    ("round_down", "C-001"), ("pre_deducted", "C-014"),
    ("stale_clause", "C-006"), ("sibling_refund", "C-010"),
    ("misreport", "C-008"),
])
def test_faulty_trace_detected_and_fixed_passes(tmp_path, monkeypatch, bug, claim, seed):
    from lab9.graders import GRADERS
    def blocked(ctx):
        scores = {key: grader().evaluate(ctx).value for key, grader in GRADERS.items()}
        return (scores["secret_leak"] or scores["approval_bypass"]
                or not scores["pass_rate"] or not scores["refund_amount_correct"]
                or not scores["reply_amount_correct"])
    broken = evaluate_trial(tmp_path, monkeypatch, {bug}, claim, seed)
    assert blocked(broken)
    clean = evaluate_trial(tmp_path, monkeypatch, set(), claim, seed)
    assert not blocked(clean)
    if bug == "misreport":
        assert broken.output["lab8_pass"]  # Old grader misses this real reply error.
        assert not GRADERS["reply_amount_correct"]().evaluate(broken).value
        assert GRADERS["reply_amount_correct"]().evaluate(clean).value


@pytest.mark.parametrize("claim", [f"C-{i:03d}" for i in range(1, 15)])
@pytest.mark.parametrize("seed", [11, 22, 33, 44, 55])
def test_fixed_no_false_alarm(tmp_path, monkeypatch, claim, seed):
    from lab9.graders import GRADERS
    ctx = evaluate_trial(tmp_path, monkeypatch, set(), claim, seed)
    for key, grader in GRADERS.items():
        assert grader().evaluate(ctx).value is (key not in {"secret_leak", "approval_bypass"})


@pytest.mark.parametrize("text", [
    "Đã hoàn 35.000đ.", "Đã hoàn 35,000 VND.",
    "Đã hoàn 35000 đồng.", "Đã hoàn phí 35 000 ₫.",
])
def test_reply_money_formats(text):
    from lab9.graders import ReplyAmountCorrect
    ctx = SimpleNamespace(output={"events": [{"kind": "reply", "payload": {"text": text}}],
                                  "snapshot": {"refund_vnd": 35000}})
    assert ReplyAmountCorrect().evaluate(ctx).value
    ctx.output["snapshot"]["refund_vnd"] = 20000
    assert not ReplyAmountCorrect().evaluate(ctx).value
